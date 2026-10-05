import math
import re
import hashlib
import json
from collections import Counter, defaultdict
from sqlalchemy.orm import Session

from ..models import Movie, WatchEvent, ProfileWatchEvent, ActiveProfile, ProfilePreference, MovieProducer
from ..protocol import AgentEnvelope, log_envelope
from ..config import get_settings
from ..security import decrypt_text

settings = get_settings()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def parse_csvish(text: str) -> list[str]:
    return [x.strip() for x in (text or "").split("|") if x.strip()]


def movie_dict(m: Movie) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "year": m.year,
        "genres": parse_csvish(m.genres),
        "runtime": m.runtime,
        "overview": m.overview,
        "rating": round(float(m.rating or 0), 1),
        "language": m.language,
        "studio": m.studio,
        "director": m.director,
        "cast": parse_csvish(m.cast),
        "moods": parse_csvish(m.moods),
        "pace": m.pace,
        "keywords": parse_csvish(m.keywords),
        "tmdb_id": m.tmdb_id,
        "poster_url": m.poster_url,
        "backdrop_url": m.backdrop_url,
        "content_rating": m.content_rating,
        "source": "tmdb" if m.tmdb_id else "curated",
    }


class PurePythonBM25:
    """Small BM25 implementation so CineSense has no NumPy build dependency."""

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = documents
        self.k1 = k1
        self.b = b
        self.n = len(documents)
        self.avgdl = (
            sum(len(doc) for doc in documents) / self.n
            if self.n
            else 0.0
        )
        self.doc_freq = Counter()
        self.term_freq = []

        for doc in documents:
            tf = Counter(doc)
            self.term_freq.append(tf)
            for term in tf:
                self.doc_freq[term] += 1

    def scores(self, query_tokens: list[str]) -> list[float]:
        scores = []
        for doc_index, doc in enumerate(self.docs):
            tf = self.term_freq[doc_index]
            dl = len(doc)
            score = 0.0
            for term in query_tokens:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                df = self.doc_freq.get(term, 0)
                idf = math.log(
                    1.0 + (self.n - df + 0.5) / (df + 0.5)
                )
                denom = (
                    freq
                    + self.k1
                    * (
                        1.0
                        - self.b
                        + self.b * (dl / (self.avgdl or 1.0))
                    )
                )
                score += idf * ((freq * (self.k1 + 1.0)) / denom)
            scores.append(score)
        return scores


class HashSemanticEncoder:
    """
    Dense semantic-style encoder that works with Python's standard library.

    It maps words and short character n-grams into a fixed-dimensional signed
    vector. Similar descriptions therefore receive overlapping vector signals,
    while no compiled scientific stack is required. If sentence-transformers
    is installed, CineSense automatically prefers that richer encoder.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _slot(self, token: str) -> tuple[int, float]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % self.dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        return index, sign

    def encode_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        words = tokenize(text)

        features = list(words)
        features.extend(
            f"{words[i]}_{words[i+1]}"
            for i in range(len(words) - 1)
        )

        compact = " ".join(words)
        if compact:
            for n in (3, 4, 5):
                features.extend(
                    compact[i:i+n]
                    for i in range(max(0, len(compact) - n + 1))
                    if " " not in compact[i:i+n]
                )

        for feature in features:
            index, sign = self._slot(feature)
            vec[index] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm:
            vec = [v / norm for v in vec]
        return vec

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.encode_one(text) for text in texts]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high <= low:
        return [0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


class RetrievalRecommendationAgent:
    name = "retrieval"

    def __init__(self):
        self._cache_key = None
        self._movies = []
        self._docs = []
        self._bm25 = None
        self._semantic_encoder = HashSemanticEncoder()
        self._semantic_matrix = []
        self._sentence_model = None
        self._semantic_backend = "pure-python-dense-hash"

    def _ensure_index(self, db: Session):
        movies = db.query(Movie).order_by(Movie.id).all()
        key = tuple(
            (m.id, m.title, m.overview, m.moods, m.keywords)
            for m in movies
        )
        if key == self._cache_key:
            return

        self._cache_key = key
        self._movies = movies
        self._docs = [
            " ".join(
                [
                    m.title,
                    m.genres,
                    m.overview,
                    m.cast,
                    m.director,
                    m.moods,
                    m.keywords,
                ]
            )
            for m in movies
        ]

        self._bm25 = PurePythonBM25(
            [tokenize(doc) for doc in self._docs]
        )

        self._sentence_model = None
        self._semantic_backend = "pure-python-dense-hash"

        if settings.enable_sentence_transformers:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_model = SentenceTransformer(
                    settings.sentence_model
                )
                raw = self._sentence_model.encode(
                    self._docs,
                    normalize_embeddings=True,
                )
                self._semantic_matrix = [
                    [float(x) for x in row]
                    for row in raw
                ]
                self._semantic_backend = "sentence-transformers"
                return
            except Exception:
                self._sentence_model = None

        self._semantic_matrix = self._semantic_encoder.encode(
            self._docs
        )

    def _semantic_query(self, query: str) -> list[float]:
        if self._sentence_model is not None:
            raw = self._sentence_model.encode(
                [query],
                normalize_embeddings=True,
            )[0]
            return [float(x) for x in raw]
        return self._semantic_encoder.encode_one(query)

    def _history_affinity(self, db: Session, user_id: int):
        genre_counts = Counter()
        mood_counts = Counter()
        if user_id <= 0:
            return genre_counts, mood_counts

        active = db.get(ActiveProfile, user_id)
        if active:
            events = (db.query(ProfileWatchEvent)
                .filter(ProfileWatchEvent.user_id == user_id, ProfileWatchEvent.profile_id == active.profile_id)
                .order_by(ProfileWatchEvent.created_at.desc()).limit(30).all())
            for event in events:
                try:
                    movie_id = int(decrypt_text(event.movie_id_enc)); movie = db.get(Movie, movie_id)
                except Exception:
                    movie = None
                if not movie: continue
                try:
                    rating = float(decrypt_text(event.rating_enc)) if event.rating_enc else 3.0
                except Exception:
                    rating = 3.0
                weight = max(0.2, 1.0 + (rating - 3) * 0.25)
                for genre in parse_csvish(movie.genres): genre_counts[genre] += weight
                for mood in parse_csvish(movie.moods): mood_counts[mood] += weight
            if events:
                return genre_counts, mood_counts

        events = (
            db.query(WatchEvent, Movie).join(Movie, Movie.id == WatchEvent.movie_id)
            .filter(WatchEvent.user_id == user_id).order_by(WatchEvent.created_at.desc()).limit(30).all()
        )
        for event, movie in events:
            weight = max(0.2, 1.0 + ((event.rating or 3) - 3) * 0.25)
            for genre in parse_csvish(movie.genres): genre_counts[genre] += weight
            for mood in parse_csvish(movie.moods): mood_counts[mood] += weight
        return genre_counts, mood_counts

    def retrieve(
        self,
        db: Session,
        envelope: AgentEnvelope,
        query: str,
        prefs: dict,
        user_id: int,
        limit: int = 12,
        explicit_ids: list[int] | None = None,
    ) -> list[dict]:
        log_envelope(db, envelope)
        self._ensure_index(db)

        if explicit_ids:
            return [
                movie_dict(movie)
                for movie in self._movies
                if movie.id in explicit_ids
            ]

        if not self._movies:
            return []

        q = query.strip() or "movie recommendation"

        lexical = normalize_scores(
            self._bm25.scores(tokenize(q))
        )

        query_vector = self._semantic_query(q)
        semantic = normalize_scores(
            [
                cosine(query_vector, doc_vector)
                for doc_vector in self._semantic_matrix
            ]
        )

        genre_hist, mood_hist = self._history_affinity(
            db,
            user_id,
        )

        wanted_genres = set(prefs.get("genres") or [])
        disliked = set(prefs.get("disliked") or [])
        mood = prefs.get("mood")
        max_runtime = prefs.get("time_available")

        # Family/profile personalization: explicit request signals stay primary,
        # while the active profile's saved preferences enrich ranking and dislikes.
        active = db.get(ActiveProfile, user_id) if user_id > 0 else None
        if active:
            stored = db.get(ProfilePreference, active.profile_id)
            if stored and stored.user_id == user_id:
                def _items(value):
                    try: return [str(x) for x in json.loads(value or "[]") if str(x).strip()]
                    except Exception: return []
                stored_genres = set(_items(stored.preferred_genres_json))
                stored_disliked = set(_items(stored.disliked_genres_json))
                stored_moods = _items(stored.preferred_moods_json)
                if not wanted_genres:
                    wanted_genres = stored_genres
                disliked |= stored_disliked
                if not mood and stored_moods:
                    mood = stored_moods[0]

        scored = []

        for i, movie in enumerate(self._movies):
            genres = set(parse_csvish(movie.genres))
            moods = set(parse_csvish(movie.moods))

            if genres & disliked:
                continue

            if max_runtime and movie.runtime > max_runtime:
                continue

            genre_match = (
                1.0
                if wanted_genres and genres & wanted_genres
                else (0.45 if not wanted_genres else 0.0)
            )

            mood_match = (
                1.0
                if mood and mood in moods
                else (0.45 if not mood else 0.0)
            )

            rating_score = min(
                max(float(movie.rating or 0) / 10.0, 0.0),
                1.0,
            )

            history_score = 0.0
            if genre_hist or mood_hist:
                gmax = max(genre_hist.values(), default=1)
                mmax = max(mood_hist.values(), default=1)
                candidates = [0.0]

                for genre in genres:
                    if genre in genre_hist:
                        candidates.append(
                            genre_hist[genre] / gmax
                        )

                for movie_mood in moods:
                    if movie_mood in mood_hist:
                        candidates.append(
                            mood_hist[movie_mood] / mmax
                        )

                history_score = max(candidates)

            # Explicit hybrid fusion.
            score = (
                0.34 * lexical[i]
                + 0.34 * semantic[i]
                + 0.14 * mood_match
                + 0.09 * genre_match
                + 0.05 * rating_score
                + 0.04 * history_score
            )

            scored.append((score, movie))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].rating,
            ),
            reverse=True,
        )

        # Responsible-AI diversification:
        # no studio may dominate the first page when alternatives exist.
        selected = []
        deferred = []
        studio_counts = defaultdict(int)

        for score, movie in scored:
            if studio_counts[movie.studio] >= 2:
                deferred.append((score, movie))
                continue

            selected.append((score, movie))
            studio_counts[movie.studio] += 1

            if len(selected) >= limit:
                break

        if len(selected) < limit:
            selected.extend(
                deferred[: limit - len(selected)]
            )

        results = []

        for score, movie in selected[:limit]:
            item = movie_dict(movie)
            reasons = []

            if mood and mood in item["moods"]:
                reasons.append(
                    f"matches your {mood.lower()} mood"
                )

            overlap = (
                wanted_genres.intersection(item["genres"])
                if wanted_genres
                else set()
            )
            if overlap:
                reasons.append(
                    "fits " + ", ".join(sorted(overlap))
                )

            if max_runtime:
                reasons.append(
                    f"fits within {max_runtime} minutes"
                )

            if not reasons:
                reasons.append(
                    "closely matches your description "
                    "and catalogue signals"
                )

            item["score"] = round(float(score), 4)
            item["semantic_backend"] = self._semantic_backend
            item["reason"] = (
                "Recommended because it "
                + ", ".join(reasons)
                + "."
            )
            results.append(item)

        return results

    def find_similar(self, db: Session, envelope: AgentEnvelope, movie_id: int, options: dict) -> dict:
        """Rank catalogue movies by an explainable, multi-factor similarity score."""
        log_envelope(db, envelope)
        self._ensure_index(db)
        source = db.get(Movie, movie_id)
        if not source:
            raise ValueError("The selected movie no longer exists.")

        valid_modes = {"cast","story","genre","year","title","director","studio","producer","mood"}
        modes = [m for m in (options.get("modes") or []) if m in valid_modes]
        if not modes:
            modes = ["story","genre"]

        presets = {
            "overall":{"story":30,"genre":20,"cast":15,"director":10,"year":8,"title":7,"studio":5,"producer":5},
            "story":{"story":55,"genre":15,"mood":10,"cast":5,"director":5,"year":5,"title":3,"studio":2},
            "cast_creators":{"cast":40,"director":25,"producer":15,"studio":10,"story":5,"genre":5},
            "genre_mood":{"genre":45,"mood":30,"story":15,"year":5,"rating":5},
            "era":{"year":60,"genre":15,"story":10,"director":5,"studio":5,"title":5},
            "different_related":{"story":30,"genre":20,"mood":15,"year":10,"rating":15,"novelty":10},
        }
        raw_weights = options.get("weights") or {}
        if raw_weights:
            weights = {k:max(0.0,float(v)) for k,v in raw_weights.items() if k in valid_modes or k in {"rating","novelty"}}
        else:
            base = presets.get(options.get("preset") or "overall", presets["overall"])
            # User-selected modes remain authoritative. Presets only change the relative weights of those selected factors.
            weights = {k:float(v) for k,v in base.items() if k in modes}
            if not weights:
                weights = {m:1.0 for m in modes}
        total = sum(weights.values()) or 1.0
        weights = {k:v/total for k,v in weights.items()}

        source_dict = movie_dict(source)
        source_cast = [x.casefold() for x in source_dict["cast"]]
        source_genres = {x.casefold() for x in source_dict["genres"]}
        source_moods = {x.casefold() for x in source_dict["moods"]}
        source_keywords = {x.casefold() for x in source_dict["keywords"]}
        source_producers = {r.producer_name.casefold() for r in db.query(MovieProducer).filter(MovieProducer.movie_id==source.id).all()}

        # Story vectors intentionally use overview + keywords + genres + moods, not title/cast/crew.
        story_texts = {}
        for m in self._movies:
            story_texts[m.id] = " ".join([m.overview or "", m.keywords or "", m.genres or "", m.moods or ""])
        if self._sentence_model is not None:
            raw=self._sentence_model.encode(list(story_texts.values()), normalize_embeddings=True)
            story_vecs={mid:[float(x) for x in row] for mid,row in zip(story_texts.keys(),raw)}
        else:
            story_vecs={mid:self._semantic_encoder.encode_one(text) for mid,text in story_texts.items()}
        source_vec=story_vecs[source.id]

        stop={"the","a","an","and","of","in","to","part"}
        def title_tokens(title): return {t for t in tokenize(title) if t not in stop and len(t)>1}
        src_title_tokens=title_tokens(source.title)
        related={
            "action":{"adventure"},"adventure":{"action","fantasy"},"horror":{"thriller"},"thriller":{"horror","mystery","crime"},
            "romance":{"drama","comedy"},"drama":{"romance"},"science fiction":{"fantasy","adventure"},"fantasy":{"science fiction","adventure"},
            "crime":{"mystery","thriller"},"mystery":{"crime","thriller"}
        }
        required=(options.get("required_genre") or "").strip().casefold()
        year_mode=options.get("year_mode") or "within_5"
        ymin=options.get("custom_year_min"); ymax=options.get("custom_year_max")
        selected_mood=(options.get("mood") or "").casefold()
        free_minutes=options.get("free_minutes")

        def year_score(year):
            diff=abs((source.year or 0)-(year or 0))
            if year_mode=="same_year": return 100.0 if diff==0 else 0.0
            if year_mode=="within_3": return max(0.0,100.0-diff*(100/4)) if diff<=3 else 0.0
            if year_mode=="within_5": return max(0.0,100.0-diff*(100/6)) if diff<=5 else 0.0
            if year_mode=="same_decade": return 100.0 if source.year//10==year//10 else max(0.0,50-diff*3)
            if year_mode=="custom" and ymin and ymax: return 100.0 if ymin<=year<=ymax else 0.0
            return max(0.0,100.0-diff*8)

        results=[]
        for candidate in self._movies:
            if candidate.id==source.id: continue
            if free_minutes and candidate.runtime>free_minutes: continue
            c=movie_dict(candidate)
            cgenres={x.casefold() for x in c["genres"]}
            if required and required not in cgenres: continue
            ccast=[x.casefold() for x in c["cast"]]
            cmoods={x.casefold() for x in c["moods"]}
            ckeywords={x.casefold() for x in c["keywords"]}
            cproducers={r.producer_name.casefold() for r in db.query(MovieProducer).filter(MovieProducer.movie_id==candidate.id).all()}

            # Leading cast receives more weight by reciprocal position.
            shared_cast=[]; cast_points=0.0; cast_den=sum(1/(i+1) for i in range(max(1,len(source_cast))))
            for i,name in enumerate(source_cast):
                if name in ccast:
                    cast_points += 1/(i+1); shared_cast.append(c["cast"][ccast.index(name)])
            cast_score=100.0*cast_points/(cast_den or 1.0)

            inter=len(source_genres & cgenres); union=len(source_genres | cgenres) or 1
            exact_genre=inter/union
            related_hits=0
            for sg in source_genres-cgenres:
                if related.get(sg,set()) & cgenres: related_hits+=1
            genre_score=min(100.0,100*exact_genre+15*related_hits)

            story_cos=max(-1.0,min(1.0,cosine(source_vec,story_vecs[candidate.id])))
            story_score=max(0.0,min(100.0,(story_cos+1.0)*50.0))
            shared_keywords=sorted(source_keywords & ckeywords)

            ctokens=title_tokens(candidate.title); title_j=len(src_title_tokens&ctokens)/(len(src_title_tokens|ctokens) or 1)
            # Lightweight normalized edit similarity without external dependencies.
            from difflib import SequenceMatcher
            title_edit=SequenceMatcher(None, re.sub(r"[^a-z0-9]","",source.title.casefold()), re.sub(r"[^a-z0-9]","",candidate.title.casefold())).ratio()
            franchise_bonus=20 if src_title_tokens & ctokens else 0
            title_score=min(100.0,(0.55*title_j+0.45*title_edit)*100+franchise_bonus)

            director_score=100.0 if source.director and candidate.director and source.director.casefold()==candidate.director.casefold() else 0.0
            studio_score=100.0 if source.studio and candidate.studio and source.studio.casefold()==candidate.studio.casefold() else 0.0
            producer_shared=source_producers & cproducers
            producer_score=100.0 if producer_shared else (50.0*len(producer_shared)/(len(source_producers|cproducers) or 1))
            mood_inter=len(source_moods & cmoods); mood_union=len(source_moods | cmoods) or 1
            mood_score=100.0*mood_inter/mood_union
            if selected_mood:
                mood_score=100.0 if selected_mood in cmoods else (70.0 if cmoods & source_moods else 25.0)
            rating_score=max(0.0,min(100.0,float(candidate.rating or 0)*10))
            novelty_score=max(0.0,100.0-(genre_score*.45+cast_score*.25+director_score*.15+studio_score*.15))
            time_fit=100.0 if not free_minutes or candidate.runtime<=free_minutes else max(0.0,100-(candidate.runtime-free_minutes)*4)

            components={
                "cast":cast_score,"story":story_score,"genre":genre_score,"year":year_score(candidate.year),"title":title_score,
                "director":director_score,"studio":studio_score,"producer":producer_score,"mood":mood_score,"rating":rating_score,
                "novelty":novelty_score,"time":time_fit,
            }
            score=sum(components.get(k,0)*w for k,w in weights.items())
            if free_minutes: score=score*.92+time_fit*.08
            matches={
                "actors":shared_cast,
                "genres":[g for g in c["genres"] if g.casefold() in source_genres],
                "director":candidate.director if director_score else "",
                "studio":candidate.studio if studio_score else "",
                "producers":[r.producer_name for r in db.query(MovieProducer).filter(MovieProducer.movie_id==candidate.id).all() if r.producer_name.casefold() in producer_shared],
                "keywords":shared_keywords[:6],
            }
            results.append({**c,"similarity":round(score,1),"components":{k:round(v,1) for k,v in components.items()},"matches":matches,"year_difference":abs(source.year-candidate.year),"fits_time":None if not free_minutes else candidate.runtime<=free_minutes})

        results.sort(key=lambda x:(x["similarity"],x["rating"]),reverse=True)
        return {"source":source_dict,"results":results[:int(options.get("limit") or 12)],"weights":{k:round(v*100,1) for k,v in weights.items()},"semantic_backend":self._semantic_backend,"producer_data_available":bool(source_producers),"year_mode":year_mode}

    def fairness_snapshot(self, db: Session) -> dict:
        self._ensure_index(db)
        by_language = Counter()
        by_studio = Counter()
        by_decade = Counter()

        for movie in self._movies:
            by_language[movie.language] += 1
            by_studio[movie.studio] += 1
            by_decade[
                f"{(movie.year // 10) * 10}s"
            ] += 1

        return {
            "total_movies": len(self._movies),
            "languages": dict(by_language),
            "studios": dict(by_studio),
            "release_decades": dict(by_decade),
            "semantic_backend": self._semantic_backend,
            "note": (
                "Recommendation results include studio "
                "diversification, and the distribution "
                "snapshot supports fairness auditing."
            ),
        }
