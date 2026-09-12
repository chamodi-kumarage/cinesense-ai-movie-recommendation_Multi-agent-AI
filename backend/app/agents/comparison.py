import math
from sqlalchemy.orm import Session
from ..protocol import AgentEnvelope, log_envelope
from ..services.llm import llm_service

MODE_WEIGHTS={
    'best_mood':      {'mood':.38,'genre':.18,'time':.12,'rating':.12,'pace':.10,'history':.10},
    'best_quality':   {'mood':.15,'genre':.15,'time':.10,'rating':.40,'pace':.08,'history':.12},
    'shortest':       {'mood':.14,'genre':.12,'time':.42,'rating':.10,'pace':.08,'history':.14},
    'most_exciting':  {'mood':.18,'genre':.13,'time':.10,'rating':.12,'pace':.35,'history':.12},
    'safest_group':   {'mood':.22,'genre':.22,'time':.18,'rating':.12,'pace':.10,'history':.16},
    'different':      {'mood':.18,'genre':.12,'time':.12,'rating':.16,'pace':.12,'history':.30},
}
MODE_LABELS={'best_mood':'Best for My Mood','best_quality':'Best Quality','shortest':'Shortest Option','most_exciting':'Most Exciting','safest_group':'Safest Group Choice','different':'Something Different'}
INTENSITY={'Gentle':20,'Measured':32,'Moderate':48,'Brisk':66,'Fast':80,'Tense':88,'Intense':96}
EXCITING_MOODS={'Thrilled','Exciting','Tense'}

def _norm(v): return max(0.0,min(100.0,float(v)))
def _mood_fit(movie,mood):
    if not mood:return 72.0
    moods=set(movie.get('moods') or [])
    if mood in moods:return 100.0
    groups=[{'Relaxed','Happy','Nostalgic','Uplifting'},{'Thrilled','Exciting','Tense'},{'Sad/Cathartic','Emotional','Reflective'},{'Romantic','Happy'}]
    for g in groups:
        if mood in g and moods & g:return 78.0
    return 38.0

def _genre_fit(movie,ctx):
    gs=set(movie.get('genres') or []); prefs=set(ctx.get('preferred_genres') or []); dislikes=set(ctx.get('disliked_genres') or [])
    if gs & dislikes:return 15.0
    if not prefs:return 70.0
    return _norm(55+18*len(gs & prefs)) if gs & prefs else 45.0

def _time_fit(runtime,free_minutes):
    if not free_minutes:return 78.0
    diff=free_minutes-runtime
    if diff<0:return _norm(35 + diff*1.7)
    if diff<=10:return 82.0
    if diff<=35:return 100.0
    if diff<=70:return 90.0
    return _norm(88-(diff-70)*.25)

def _pace_fit(movie,mood,less_intense=False):
    val=INTENSITY.get(movie.get('pace') or 'Moderate',50)
    if less_intense or mood in {'Relaxed','Nostalgic','Romantic'}:return _norm(110-val)
    if mood in {'Thrilled','Exciting','Tense'}:return _norm(40+val*.65)
    return _norm(88-abs(val-55)*.55)

def _history_fit(movie,ctx,different=False):
    gs=set(movie.get('genres') or []); hist=set(ctx.get('history_genres') or []); prefs=set(ctx.get('preferred_genres') or [])
    familiarity=min(100,45+18*len(gs & (hist|prefs))) if (hist or prefs) else 58
    return 100-familiarity*.65 if different else familiarity

def _risk(movie,criteria,ctx,free_minutes,mood):
    reasons=[]; points=0
    if free_minutes and movie['runtime']>free_minutes:
        over=movie['runtime']-free_minutes;points+=min(45,20+over*.8);reasons.append(f'Runtime exceeds your available time by {over} minutes.')
    disliked=set(ctx.get('disliked_genres') or []) & set(movie.get('genres') or [])
    if disliked:points+=30;reasons.append('Includes a genre you usually avoid: '+', '.join(sorted(disliked))+'.')
    if criteria['mood']<55:points+=18;reasons.append('Only a partial match for your selected mood.')
    if mood in {'Relaxed','Nostalgic','Romantic'} and INTENSITY.get(movie.get('pace'),50)>=80:points+=18;reasons.append('This may feel too intense for a calmer evening.')
    pref_lang=ctx.get('preferred_language')
    if pref_lang and movie.get('language') and movie['language']!=pref_lang:points+=8;reasons.append(f"It is in {movie['language']}, which differs from your usual language.")
    score=int(_norm(points)); level='Low' if score<25 else ('Medium' if score<55 else 'High')
    if not reasons:reasons.append('Fits the current mood, time and preference signals with no major conflict detected.')
    return score,level,reasons

class ComparisonExplainabilityAgent:
    name='comparison'
    def _score_rows(self,movies,mood,mode,free_minutes,ctx,scenario_info):
        weights=dict(MODE_WEIGHTS.get(mode,MODE_WEIGHTS['best_mood']))
        if scenario_info.get('rating_priority'):
            weights['rating']+=.22;weights['mood']=max(.08,weights['mood']-.15);total=sum(weights.values());weights={k:v/total for k,v in weights.items()}
        rows=[]
        remove_genre=scenario_info.get('remove_genre')
        for m in movies:
            criteria={
                'mood':_mood_fit(m,mood),
                'genre':_genre_fit(m,ctx),
                'time':_time_fit(m['runtime'],free_minutes),
                'rating':_norm((float(m.get('rating') or 0)/10)*100),
                'pace':_pace_fit(m,mood,scenario_info.get('less_intense',False)),
                'history':_history_fit(m,ctx,mode=='different'),
            }
            penalty=0
            if remove_genre and any(remove_genre.lower()==g.lower() for g in m.get('genres') or []): penalty=40
            overall=sum(criteria[k]*weights[k] for k in weights)-penalty
            risk_score,risk_level,risk_reasons=_risk(m,criteria,ctx,free_minutes,mood)
            rows.append({'id':m['id'],'title':m['title'],'year':m.get('year'),'poster_url':m.get('poster_url'),'mood_fit':round(criteria['mood']),
                'genre_fit':round(criteria['genre']),'time_fit':round(criteria['time']),'rating_fit':round(criteria['rating']),
                'pace_fit':round(criteria['pace']),'history_fit':round(criteria['history']),'overall_score':round(_norm(overall)),
                'pace':m.get('pace'),'tone':', '.join((m.get('moods') or [])[:2]) or 'Balanced','runtime':m['runtime'],
                'rating':m['rating'],'genres':m.get('genres') or [],'moods':m.get('moods') or [],'risk_score':risk_score,'risk_level':risk_level,'risk_reasons':risk_reasons})
        return sorted(rows,key=lambda r:(r['overall_score'],r['rating'],-r['runtime']),reverse=True),weights

    async def compare(self,db:Session,envelope:AgentEnvelope,movies:list[dict],mood=None,user_note=None,mode='best_mood',free_minutes=None,profile_context=None,scenario_info=None):
        log_envelope(db,envelope);ctx=profile_context or {};scenario_info=scenario_info or {}
        base_rows,_=self._score_rows(movies,mood,mode,free_minutes,ctx,{})
        rows,weights=self._score_rows(movies,mood,mode,scenario_info.get('free_minutes',free_minutes),ctx,scenario_info)
        winner=rows[0] if rows else None
        base_pos={r['id']:i+1 for i,r in enumerate(base_rows)};changes=[]
        for i,r in enumerate(rows,1):
            old=base_pos.get(r['id'],i)
            r['previous_rank']=old;r['rank']=i;r['rank_change']=old-i
            if old!=i:
                direction='moved up' if i<old else 'moved down'
                changes.append(f"{r['title']} {direction} from {old} to {i} because the new condition changed its fit score.")
        facts='\n'.join(f"- {m['title']} ({m['year']}): genres={m['genres']}; moods={m['moods']}; pace={m['pace']}; runtime={m['runtime']} min; rating={m['rating']}/10" for m in movies)
        prompt=f"Give a concise grounded comparison verdict for mode {MODE_LABELS.get(mode,mode)}"+(f" and mood {mood}" if mood else '')+(f". Scenario: {scenario_info.get('raw')}" if scenario_info.get('raw') else '')+". Use only supplied catalogue facts. Mention the winner and one trade-off."
        text=await llm_service.chat(prompt,facts)
        if not text and winner:
            text=f"{winner['title']} ranks first in {MODE_LABELS.get(mode,mode)} mode with {winner['overall_score']}% suitability. Its strongest factors are " + ', '.join(sorted([('mood',winner['mood_fit']),('genre',winner['genre_fit']),('time',winner['time_fit']),('rating',winner['rating_fit']),('pace',winner['pace_fit'])],key=lambda x:x[1],reverse=True)[:2][i][0] for i in range(2)) + f". Decision risk is {winner['risk_level'].lower()}."
        return {'rows':rows,'winner_id':winner['id'] if winner else None,'explanation':text or 'Choose at least two valid movies.','mode':mode,'mode_label':MODE_LABELS.get(mode,mode),'weights':{k:round(v*100) for k,v in weights.items()},'ranking_changes':changes,'scenario':scenario_info.get('raw') or '', 'free_minutes':scenario_info.get('free_minutes',free_minutes)}

    def explain_similarity(self, db: Session, envelope: AgentEnvelope, source: dict, ranked: list[dict], selected_modes: list[str]) -> list[dict]:
        """Create grounded, user-facing reasons from already-calculated similarity facts."""
        log_envelope(db, envelope)
        labels={"cast":"cast","story":"story","genre":"genre","year":"release period","title":"title","director":"director","studio":"studio","producer":"producer","mood":"mood"}
        output=[]
        for row in ranked:
            reasons=[]; matches=row.get("matches") or {}; comp=row.get("components") or {}
            if "cast" in selected_modes and matches.get("actors"):
                reasons.append("shared cast: "+", ".join(matches["actors"][:3]))
            if "director" in selected_modes and matches.get("director"):
                reasons.append(f"same director, {matches['director']}")
            if "studio" in selected_modes and matches.get("studio"):
                reasons.append(f"same studio, {matches['studio']}")
            if "producer" in selected_modes and matches.get("producers"):
                reasons.append("shared producer: "+", ".join(matches["producers"][:2]))
            if "genre" in selected_modes and matches.get("genres"):
                reasons.append("matching genres: "+", ".join(matches["genres"][:3]))
            if "story" in selected_modes:
                if matches.get("keywords"):
                    reasons.append("shared story themes: "+", ".join(matches["keywords"][:4]))
                else:
                    reasons.append(f"{comp.get('story',0):.0f}% semantic story similarity")
            if "year" in selected_modes:
                d=row.get("year_difference",0)
                reasons.append("same release year" if d==0 else f"released {d} year{'s' if d!=1 else ''} apart")
            if "title" in selected_modes:
                reasons.append(f"{comp.get('title',0):.0f}% title-pattern similarity; title similarity does not imply story similarity")
            if "mood" in selected_modes and comp.get("mood",0)>=50:
                reasons.append(f"{comp.get('mood',0):.0f}% mood compatibility")
            if not reasons:
                strongest=sorted(((k,v) for k,v in comp.items() if k in labels), key=lambda x:x[1], reverse=True)[:2]
                reasons=[f"strong {labels.get(k,k)} match ({v:.0f}%)" for k,v in strongest]
            row=dict(row)
            row["why_similar"]="Similar because " + "; ".join(reasons[:4]) + "."
            output.append(row)
        return output

