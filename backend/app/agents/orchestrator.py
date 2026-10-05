from datetime import datetime,timezone,timedelta
import json,re,uuid
from sqlalchemy.orm import Session
from ..models import User,ChatTurn,AIUsage,ProfileConversationState,Movie,Profile,PlannerActivity,ActiveProfile,ProfilePreference
from ..security import encrypt_text,decrypt_text
from ..protocol import AgentEnvelope
from ..config import get_settings
from ..services.llm import llm_service
from .guardian import GuardianAgent
from .mood import MoodPreferenceAgent
from .retrieval import RetrievalRecommendationAgent
from .comparison import ComparisonExplainabilityAgent
from .scheduler import MoodTimeSchedulerAgent
from ..services.profiles import active_profile_id

settings=get_settings()

class ConversationalOrchestratorAgent:
    name="orchestrator"
    def __init__(self):
        self.guardian=GuardianAgent();self.mood=MoodPreferenceAgent();self.retrieval=RetrievalRecommendationAgent()
        self.comparison=ComparisonExplainabilityAgent();self.scheduler=MoodTimeSchedulerAgent()

    def _env(self,trace_id,receiver,intent,payload,user_id=None):
        return AgentEnvelope(trace_id=trace_id,sender=self.name,receiver=receiver,intent=intent,user_id=user_id,payload=payload)

    def _history(self,db,user_id,profile_id):
        cutoff=datetime.now(timezone.utc)-timedelta(days=settings.chat_retention_days)
        for row in db.query(ChatTurn).filter(ChatTurn.user_id==user_id,ChatTurn.profile_id==profile_id,ChatTurn.created_at<cutoff).all():db.delete(row)
        db.commit()
        rows=db.query(ChatTurn).filter(ChatTurn.user_id==user_id,ChatTurn.profile_id==profile_id).order_by(ChatTurn.created_at.desc()).limit(10).all()
        rows.reverse()
        return [{"role":r.role,"content":decrypt_text(r.content_enc)} for r in rows]

    def _remember(self,db,user_id,profile_id,role,content):
        db.add(ChatTurn(user_id=user_id,profile_id=profile_id,role=role,content_enc=encrypt_text(content)));db.commit()
        rows=db.query(ChatTurn).filter(ChatTurn.user_id==user_id,ChatTurn.profile_id==profile_id).order_by(ChatTurn.created_at.desc()).all()
        for row in rows[10:]:db.delete(row)
        db.commit()

    def _load_state(self,db,profile_id):
        row=db.get(ProfileConversationState,profile_id)
        if not row:return {"last_query":"","prefs":{},"movie_ids":[]}
        try:prefs=json.loads(row.prefs_json or "{}")
        except Exception:prefs={}
        try:movie_ids=json.loads(row.movie_ids_json or "[]")
        except Exception:movie_ids=[]
        return {"last_query":decrypt_text(row.last_query_enc),"prefs":prefs,"movie_ids":movie_ids}

    def _save_state(self,db,profile_id,query,prefs,movie_ids):
        row=db.get(ProfileConversationState,profile_id)
        if not row:
            row=ProfileConversationState(profile_id=profile_id);db.add(row)
        row.last_query_enc=encrypt_text(query or "")
        row.prefs_json=json.dumps(prefs or {},ensure_ascii=False)
        row.movie_ids_json=json.dumps(movie_ids or [])
        db.commit()

    def _apply_profile_content_filters(self,db,profile_id,movies):
        profile=db.get(Profile,profile_id)
        if not profile:return movies
        from ..services.family_logic import movie_allowed_for_profiles
        filtered=[]
        for item in movies:
            movie=db.get(Movie,item.get("id"))
            if movie and movie_allowed_for_profiles(movie,[profile],db):filtered.append(item)
        return filtered

    def _intent(self,text):
        t=text.lower()
        if any(x in t for x in ["compare","which one","which should i","first two","these two","better choice"]):return "compare"
        if any(x in t for x in ["plan my","watch plan","double feature","finish before","finish by","schedule"]):return "schedule"
        return "recommend"

    def _finish_by(self,text):
        t=text.lower()
        m=re.search(r"(?:before|by)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",t)
        if not m:return None
        h=int(m.group(1));minute=int(m.group(2) or 0);ampm=m.group(3)
        if ampm=="pm" and h<12:h+=12
        if ampm=="am" and h==12:h=0
        if not ampm and h<=7:h+=12
        return f"{h%24:02d}:{minute:02d}"

    def _consume_quota(self,db,user):
        if user.plan!="free":return
        today=datetime.now(timezone.utc).date().isoformat()
        usage=db.query(AIUsage).filter(AIUsage.user_id==user.id,AIUsage.usage_date==today).first()
        if not usage:usage=AIUsage(user_id=user.id,usage_date=today,count=0);db.add(usage)
        if usage.count>=10:raise ValueError("You’ve reached the Free plan’s 10 AI conversations for today. Browsing remains available; Premium removes this daily AI limit.")
        usage.count+=1;db.commit()

    def _movie_question(self, db, text):
        """Return a catalogue movie when the user clearly asks about a named title."""
        normalized = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return None
        movies = db.query(Movie).all()
        matches = []
        for movie in movies:
            title = re.sub(r"[^a-z0-9 ]+", " ", movie.title.lower()).strip()
            if not title:
                continue
            if title in normalized:
                matches.append((len(title), movie))
        return max(matches, key=lambda item: item[0])[1] if matches else None

    def _movie_info_reply(self, movie, question):
        genres = ", ".join([g.strip() for g in (movie.genres or "").split(",") if g.strip()])
        cast = ", ".join([c.strip() for c in (movie.cast or "").split(",") if c.strip()][:4])
        parts = [
            f"{movie.title} ({movie.year}) is a {genres.lower() if genres else 'feature'} film directed by {movie.director or 'an unlisted director'}.",
            movie.overview.strip(),
            f"It runs {movie.runtime} minutes and has a catalogue rating of {movie.rating}/10."
        ]
        if cast:
            parts.append(f"The listed cast includes {cast}.")
        lower = question.lower()
        if any(word in lower for word in ["worth", "good", "recommend", "should i watch"]):
            parts.append(f"If you enjoy {genres.lower() if genres else 'this kind of film'}, it is a strong option to consider.")
        return " ".join(p for p in parts if p)

    def _local_reply(self,message,prefs,movies):
        lower=message.lower().strip()
        if re.fullmatch(r"(hi|hello|hey|thanks|thank you|good morning|good evening)[!. ]*",lower):
            return "Hi, I’m CineSense. Tell me a movie title, the mood you want, a genre, or how much time you have, and I’ll help you choose something that fits."
        if not movies:
            return "I couldn’t find a strong match with those exact preferences. Try relaxing one constraint, such as runtime or genre, and I’ll narrow it down again."
        mood=f" for a {prefs['mood'].lower()} mood" if prefs.get("mood") else ""
        intro=f"Here are a few good matches{mood}:"
        items=[]
        for m in movies[:3]:
            reason=(m.get("reason") or "It fits your request.").strip()
            items.append(f"{m['title']} ({m['year']}) — {reason} {m['runtime']} min, {m['rating']}/10.")
        return intro+"\n"+"\n".join(items)+"\nTell me if you want something shorter, lighter, more intense, or if you want to compare two of them."

    async def chat(self,db,user,message,mood_override=None,dismissed_moods=None):
        profile_id=active_profile_id(db,user)
        self._consume_quota(db,user);trace_id=str(uuid.uuid4());history=self._history(db,user.id,profile_id)
        state=self._load_state(db,profile_id)
        guard=self.guardian.inspect_input(db,self._env(trace_id,"guardian","inspect_input",{"message":message},user.id),message)
        if not guard["safe"]:
            response=self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"safety"},user.id),guard["notice"])
            self._remember(db,user.id,profile_id,"user",message);self._remember(db,user.id,profile_id,"assistant",response)
            return {"trace_id":trace_id,"reply":response,"preferences":state.get("prefs",{}),"movies":[],"safety":guard["risk"]}

        clean=guard["sanitized"]

        named_movie = self._movie_question(db, clean)
        info_words = ["about", "what is", "tell me", "who", "director", "cast", "plot", "story", "runtime", "rating", "source code", "worth watching", "good movie"]
        if named_movie and any(word in clean.lower() for word in info_words):
            from ..services.family_logic import movie_allowed_for_profiles
            profile=db.get(Profile,profile_id)
            if profile and not movie_allowed_for_profiles(named_movie,[profile],db):
                named_movie=None
        if named_movie and any(word in clean.lower() for word in info_words):
            from .retrieval import movie_dict
            grounded = movie_dict(named_movie)
            reply = self._movie_info_reply(named_movie, clean)
            reply = self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"movie_information"},user.id),reply)
            self._remember(db,user.id,profile_id,"user",clean); self._remember(db,user.id,profile_id,"assistant",reply)
            self._save_state(db,profile_id,clean,state.get("prefs") or {},[named_movie.id])
            return {"trace_id":trace_id,"reply":reply,"preferences":state.get("prefs") or {},"movies":[grounded],"safety":guard["risk"],"ai_provider":"catalogue-grounded"}

        current=self.mood.analyze(db,self._env(trace_id,"mood_preference","analyze",{"message":clean},user.id),clean,mood_override,dismissed_moods)
        previous=state.get("prefs") or {}
        prefs={
            "genres":current.get("genres") or previous.get("genres") or [],
            "mood":current.get("mood") or previous.get("mood"),
            "time_available":current.get("time_available") or previous.get("time_available"),
            "disliked":list(dict.fromkeys((previous.get("disliked") or [])+(current.get("disliked") or []))),
            "entities":current.get("entities") or previous.get("entities") or [],
            "detected_moods":current.get("detected_moods") or previous.get("detected_moods") or []
        }

        lower=clean.lower()
        if "less intense" in lower or "calmer" in lower:
            prefs["mood"]="Relaxed"
        if "shorter" in lower and not current.get("time_available") and state.get("movie_ids"):
            previous_movies=self.retrieval.retrieve(
                db,self._env(trace_id,"retrieval","fetch_previous_context",{"movie_ids":state["movie_ids"]},user.id),
                "",{},user.id,explicit_ids=state["movie_ids"])
            previous_movies=self._apply_profile_content_filters(db,profile_id,previous_movies)
            if previous_movies:
                prefs["time_available"]=max(60,min(m["runtime"] for m in previous_movies)-10)

        intent=self._intent(clean)
        if intent=="compare" and len(state.get("movie_ids",[]))>=2:
            n=3 if "three" in lower or "first 3" in lower else 2
            ids=state["movie_ids"][:n]
            grounded=self.retrieval.retrieve(
                db,self._env(trace_id,"retrieval","fetch_grounding",{"movie_ids":ids},user.id),
                "",{},user.id,explicit_ids=ids)
            grounded=self._apply_profile_content_filters(db,profile_id,grounded)
            result=await self.comparison.compare(
                db,self._env(trace_id,"comparison","compare_from_chat",{"movie_ids":ids,"mood":prefs.get("mood")},user.id),
                grounded,prefs.get("mood"),clean)
            reply=self.guardian.inspect_output(
                db,self._env(trace_id,"guardian","inspect_output",{"response_type":"comparison_chat"},user.id),
                result["explanation"])
            self._remember(db,user.id,profile_id,"user",clean);self._remember(db,user.id,profile_id,"assistant",reply)
            self._save_state(db,profile_id,clean,prefs,ids)
            return {"trace_id":trace_id,"reply":reply,"preferences":prefs,"movies":grounded,
                    "comparison":result,"safety":"low",
                    "ai_provider":settings.llm_provider if llm_service.enabled else "offline-demo"}

        if intent=="schedule":
            if user.plan=="free":
                reply=("The full mood-and-time scheduler—including double-feature planning—is a Premium/Family feature in the project’s pricing model. "
                       "You can still use Free recommendations and comparisons within the daily AI allowance, or use the included demo account to evaluate the complete scheduler flow.")
                self._remember(db,user.id,profile_id,"user",clean);self._remember(db,user.id,profile_id,"assistant",reply)
                return {"trace_id":trace_id,"reply":reply,"preferences":prefs,"movies":[],"safety":"low"}
            finish_by=self._finish_by(clean)
            if not prefs.get("time_available"):
                reply=("I can absolutely turn this into a watch plan, but I’m missing one practical constraint: how many minutes of free time do you have? "
                       "You can answer naturally, for example “about 2 hours” or “150 minutes, and I need to finish before 11pm.” "
                       "I’ll keep your current mood and genre preferences while I wait for that one detail.")
                self._remember(db,user.id,profile_id,"user",clean);self._remember(db,user.id,profile_id,"assistant",reply)
                self._save_state(db,profile_id,clean,prefs,state.get("movie_ids",[]))
                return {"trace_id":trace_id,"reply":reply,"preferences":prefs,"movies":[],"safety":"low"}
            candidates=self.retrieval.retrieve(
                db,self._env(trace_id,"retrieval","schedule_candidates",{"genres":prefs["genres"],"mood":prefs["mood"],"runtime":prefs["time_available"]},user.id),
                clean,prefs,user.id,limit=12)
            candidates=self._apply_profile_content_filters(db,profile_id,candidates)
            plan=self.scheduler.plan(
                db,self._env(trace_id,"scheduler","build_plan_from_chat",{"candidate_count":len(candidates),"free_minutes":prefs["time_available"],"finish_by":finish_by},user.id),
                candidates,prefs["time_available"],finish_by)
            titles=", ".join(m["title"] for m in plan["movies"]) or "no matching title"
            reply=(plan["message"]+"\n\n"+(f"Your plan is {titles}. " if plan["movies"] else "")+
                   "If you want, I can now make the plan lighter, more intense, shorter, or compare the selected films without losing this conversation context.")
            reply=self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"schedule_chat"},user.id),reply)
            ids=[m["id"] for m in plan["movies"]]
            self._remember(db,user.id,profile_id,"user",clean);self._remember(db,user.id,profile_id,"assistant",reply)
            self._save_state(db,profile_id,clean,prefs,ids or state.get("movie_ids",[]))
            return {"trace_id":trace_id,"reply":reply,"preferences":prefs,"movies":plan["movies"],
                    "plan":plan,"safety":"low","ai_provider":settings.llm_provider if llm_service.enabled else "offline-demo"}

        conversational_only=bool(re.fullmatch(r"\s*(hi|hello|hey|thanks|thank you|good morning|good evening)[!. ]*\s*",clean.lower()))
        movies=[] if conversational_only else self.retrieval.retrieve(
            db,self._env(trace_id,"retrieval","recommend",{"query":clean,"mood":prefs.get("mood"),"genres":prefs.get("genres"),"runtime":prefs.get("time_available")},user.id),
            clean,prefs,user.id,limit=50)
        movies=self._apply_profile_content_filters(db,profile_id,movies)
        context="\\n".join(f"{m['title']} ({m['year']}), genres {m['genres']}, moods {m['moods']}, runtime {m['runtime']}, rating {m['rating']}, overview: {m['overview']}" for m in movies[:5])
        prompt=(f"User message: {clean}\\nDetected preferences: {json.dumps(prefs)}\\nReply as a friendly movie companion. "
                "Be detailed enough to be genuinely helpful, not abrupt. Recommend up to three supplied catalogue options and explain each match. "
                "Treat the user's message as a follow-up when recent history exists. Never invent facts.")
        reply=await llm_service.chat(prompt,context,history) or self._local_reply(clean,prefs,movies)
        reply=self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"chat","movie_count":len(movies)},user.id),reply)
        self._remember(db,user.id,profile_id,"user",clean);self._remember(db,user.id,profile_id,"assistant",reply)
        if movies:self._save_state(db,profile_id,clean,prefs,[m["id"] for m in movies[:4]])
        elif current.get("mood") or current.get("genres") or current.get("time_available"):self._save_state(db,profile_id,clean,prefs,state.get("movie_ids",[]))
        return {"trace_id":trace_id,"reply":reply,"preferences":prefs,"movies":movies[:10],"safety":guard["risk"],
                "ai_provider":settings.llm_provider if llm_service.enabled else "offline-demo"}

    def _comparison_profile_context(self,db,user):
        profile_id=active_profile_id(db,user)
        pref=db.get(ProfilePreference,profile_id)
        def load(value):
            try:return json.loads(value or "[]")
            except Exception:return []
        genre_hist,mood_hist=self.retrieval._history_affinity(db,user.id)
        return {
            "profile_id":profile_id,
            "preferred_genres":load(pref.preferred_genres_json) if pref else [],
            "disliked_genres":load(pref.disliked_genres_json) if pref else [],
            "preferred_moods":load(pref.preferred_moods_json) if pref else [],
            "history_genres":[x for x,_ in genre_hist.most_common(5)],
            "history_moods":[x for x,_ in mood_hist.most_common(5)],
            "preferred_language":"English",
        }

    def _parse_comparison_scenario(self,text):
        t=(text or "").strip(); low=t.lower(); info={"raw":t}
        m=re.search(r"(?:only|have|got|within|under)\s+(\d{2,3})\s*(?:minutes?|mins?)",low)
        if m:info["free_minutes"]=max(30,min(600,int(m.group(1))))
        h=re.search(r"(\d+(?:\.\d+)?)\s*hours?",low)
        if h and "free_minutes" not in info:info["free_minutes"]=max(30,min(600,int(float(h.group(1))*60)))
        if any(x in low for x in ["less intense","calmer","not intense","lower intensity"]):info["less_intense"]=True
        if "rating" in low and any(x in low for x in ["more than mood","matters more","prioritize rating","prioritise rating"]):info["rating_priority"]=True
        m=re.search(r"(?:remove|no|without|avoid)\s+([a-z][a-z -]{2,30})",low)
        if m:
            candidate=m.group(1).strip().title()
            known={"Horror","Comedy","Drama","Action","Romance","Thriller","Crime","Fantasy","Animation","Adventure","Science Fiction","Family","Mystery","War","Western"}
            for g in known:
                if g.lower() in candidate.lower():info["remove_genre"]=g;break
        return info

    async def compare_movies(self,db,user,movie_ids,mood,user_note,mode="best_mood",free_minutes=None,scenario=None):
        self._consume_quota(db,user);trace_id=str(uuid.uuid4())
        # Guardian protects free-text comparison inputs before any agent interprets them.
        free_text=" ".join(x for x in [user_note or "",scenario or ""] if x).strip()
        if free_text:
            guarded=self.guardian.inspect_input(db,self._env(trace_id,"guardian","inspect_input",{"comparison_text":free_text}),free_text)
            if not guarded["safe"]:raise ValueError(guarded["notice"])
            free_text=guarded["sanitized"]
        scenario_info=self._parse_comparison_scenario(free_text or scenario)
        # Mood & Preference Agent may extract an implied mood from the what-if text; explicit UI mood stays authoritative.
        mood_signal=self.mood.analyze(db,self._env(trace_id,"mood_preference","comparison_context",{"text":free_text}),free_text or "compare these movies",mood,[]) if free_text else {"mood":mood}
        effective_mood=mood or mood_signal.get("mood")
        profile_id=active_profile_id(db,user)
        movies=self.retrieval.retrieve(db,self._env(trace_id,"retrieval","fetch_grounding",{"movie_ids":movie_ids}),"",{},user.id,explicit_ids=movie_ids)
        movies=self._apply_profile_content_filters(db,profile_id,movies)
        if len(movies)<2:raise ValueError("Please choose at least two valid movies.")
        effective_minutes=scenario_info.get("free_minutes",free_minutes)
        # Scheduler Agent contributes explicit time feasibility using the same shortlisted catalogue facts.
        schedule_budget=int(effective_minutes or max(m["runtime"] for m in movies))
        schedule_check=self.scheduler.plan(db,self._env(trace_id,"scheduler","comparison_time_check",{"movie_ids":movie_ids,"free_minutes":schedule_budget}),movies,schedule_budget,None,0)
        profile_context=self._comparison_profile_context(db,user)
        result=await self.comparison.compare(db,self._env(trace_id,"comparison","compare",{"movie_ids":movie_ids,"mood":effective_mood,"mode":mode,"scenario":scenario or ""}),movies,effective_mood,user_note,mode,free_minutes,profile_context,scenario_info)
        result["scheduler_check"]={"budget_minutes":schedule_budget,"fitting_movie_ids":[m["id"] for m in movies if m["runtime"]<=schedule_budget],"message":schedule_check.get("message","")}
        result["mood_signal"]={"effective_mood":effective_mood,"source":"explicit" if mood else "mood_preference_agent"}
        result["explanation"]=self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"comparison"}),result["explanation"])
        result["trace_id"]=trace_id;return result

    async def find_similar(self, db, user, movie_id, modes, weights=None, preset="overall", required_genre=None, year_mode="within_5", custom_year_min=None, custom_year_max=None, mood=None, free_minutes=None, limit=12):
        self._consume_quota(db,user); trace_id=str(uuid.uuid4())
        profile_id=active_profile_id(db,user)
        source_movie=db.get(Movie,movie_id)
        from ..services.family_logic import movie_allowed_for_profiles
        profile=db.get(Profile,profile_id)
        if source_movie and profile and not movie_allowed_for_profiles(source_movie,[profile],db):
            raise ValueError("This movie is hidden by the active profile's content filters.")
        allowed={"cast","story","genre","year","title","director","studio","producer","mood"}
        clean_modes=[m for m in (modes or []) if m in allowed]
        if not clean_modes: clean_modes=["story","genre"]
        if required_genre:
            guarded=self.guardian.inspect_input(db,self._env(trace_id,"guardian","inspect_input",{"similarity_filter":required_genre}),required_genre)
            if not guarded["safe"]: raise ValueError(guarded["notice"])
            required_genre=guarded["sanitized"][:50]
        options={"modes":clean_modes,"weights":weights or {},"preset":preset,"required_genre":required_genre,"year_mode":year_mode,"custom_year_min":custom_year_min,"custom_year_max":custom_year_max,"mood":mood,"free_minutes":free_minutes,"limit":limit}
        # Explicit mood and time conditions remain delegated to their existing specialists.
        if mood:
            mood_signal=self.mood.analyze(db,self._env(trace_id,"mood_preference","similarity_context",{"mood":mood}),f"Find something similar but {mood}",mood,[])
            options["mood"]=mood_signal.get("mood") or mood
        raw=self.retrieval.find_similar(db,self._env(trace_id,"retrieval","find_similar",{"movie_id":movie_id,"modes":clean_modes,"preset":preset}),movie_id,options)
        raw["results"]=[row for row in raw["results"] if (movie:=db.get(Movie,row["id"])) and (not profile or movie_allowed_for_profiles(movie,[profile],db))]
        if free_minutes and raw["results"]:
            self.scheduler.plan(db,self._env(trace_id,"scheduler","similarity_time_filter",{"free_minutes":free_minutes}),raw["results"][:12],free_minutes,None,0)
        raw["results"]=self.comparison.explain_similarity(db,self._env(trace_id,"comparison","explain_similarity",{"movie_id":movie_id,"result_count":len(raw["results"])}),raw["source"],raw["results"],clean_modes)
        for row in raw["results"]:
            row["why_similar"]=self.guardian.inspect_output(db,self._env(trace_id,"guardian","inspect_output",{"response_type":"similarity_explanation"}),row["why_similar"])
        raw.update({"trace_id":trace_id,"modes":clean_modes,"intent":"find_similar"})
        return raw

    def build_plan(self,db,user,genres,mood,free_minutes,finish_by,query,buffer_minutes=0):
        if user.plan=="free":
            raise ValueError("The mood scheduler and double-feature planner are Premium/Family features in the project pricing model. Use the demo account to evaluate the complete planner flow.")
        self._consume_quota(db,user);trace_id=str(uuid.uuid4())
        normalized_finish=None
        if finish_by:
            if re.fullmatch(r"\d{2}:\d{2}", finish_by.strip()):
                normalized_finish=finish_by.strip()
            else:
                normalized_finish=self._finish_by(finish_by)
        if not normalized_finish and query:
            normalized_finish=self._finish_by(query)
        effective_minutes=max(int(free_minutes)-int(buffer_minutes or 0),1)
        profile_id=active_profile_id(db,user)
        text=query or f"{' '.join(genres)} {mood or ''} {effective_minutes} minutes"
        prefs={"genres":genres,"mood":mood,"time_available":effective_minutes,"disliked":[]}
        candidates=self.retrieval.retrieve(db,self._env(trace_id,"retrieval","schedule_candidates",{"genres":genres,"mood":mood,"runtime":effective_minutes}),text,prefs,user.id,limit=60)
        candidates=self._apply_profile_content_filters(db,profile_id,candidates)
        result=self.scheduler.plan(
            db,
            self._env(trace_id,"scheduler","build_plan",{"candidate_count":len(candidates),"free_minutes":free_minutes,"finish_by":normalized_finish,"buffer_minutes":buffer_minutes}),
            candidates,free_minutes,normalized_finish,buffer_minutes
        )

        genre_hist,mood_hist=self.retrieval._history_affinity(db,user.id)
        hist_genre=genre_hist.most_common(1)[0][0] if genre_hist else None
        hist_mood=mood_hist.most_common(1)[0][0] if mood_hist else None
        context_bits=[]
        if mood: context_bits.append(f"you’re planning for a {mood.lower()} mood")
        context_bits.append(f"you have {free_minutes} minutes")
        if genres: context_bits.append(f"you asked for {', '.join(genres)}")
        if hist_genre and hist_genre not in genres: context_bits.append(f"your recent history leans toward {hist_genre}")
        elif hist_mood and hist_mood != mood: context_bits.append(f"you often watch {hist_mood.lower()} titles")
        if result.get("movies"):
            lead=result["movies"][0]
            fit=[]
            if mood and mood in (lead.get("moods") or []): fit.append(f"matches your {mood.lower()} mood")
            if lead.get("runtime",0)<=effective_minutes: fit.append("fits the time window")
            if genres and set(genres)&set(lead.get("genres") or []): fit.append("matches your genre choice")
            result["why_this_plan"]="You said " + ", ".join(context_bits) + ". " + lead["title"] + " " + (", ".join(fit) if fit else "is the strongest grounded fit from your current options") + "."
            for movie in result["movies"]:
                movie["personal_reason"] = f"Fits your {mood.lower() + ' mood' if mood else 'current preferences'} and stays inside your available watch time."
        else:
            result["why_this_plan"]="No catalogue movie fits all of the current time and preference constraints yet."

        profile_id=active_profile_id(db,user)
        db.add(PlannerActivity(
            user_id=user.id,profile_id=profile_id,mood=mood or "",
            genres_json=json.dumps(genres or []),movie_ids_json=json.dumps([m["id"] for m in result.get("movies",[])]),
            free_minutes=int(free_minutes),used_minutes=int(result.get("used_minutes",0)),buffer_minutes=int(buffer_minutes or 0),
            finish_by=normalized_finish or "",plan_type=result.get("type","none")
        ))
        db.commit()
        result["trace_id"]=trace_id;return result

orchestrator=ConversationalOrchestratorAgent()
