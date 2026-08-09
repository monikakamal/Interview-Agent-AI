import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from models.schemas import (
    CandidateProfile,
    CandidatesData,
    CurriculumData,
    CurriculumDay,
)


class DataRetriever:
    """
    Loads and retrieves candidate and curriculum information.

    Expected project structure:

        project_root/
        ├── data/
        │   ├── candidates.json
        │   └── curriculum.json
        ├── models/
        │   └── schemas.py
        └── retriever.py
    """

    def __init__(
        self,
        candidates_path: Optional[str] = None,
        curriculum_path: Optional[str] = None,
    ) -> None:
        """
        Initialize the data retriever.

        If paths are not provided, data is loaded from the project's
        data/ directory.
        """

        base_dir = Path(__file__).resolve().parent

        self.candidates_path = (
            Path(candidates_path)
            if candidates_path
            else base_dir / "data" / "candidates.json"
        )

        self.curriculum_path = (
            Path(curriculum_path)
            if curriculum_path
            else base_dir / "data" / "curriculum.json"
        )

        self._candidates_cache: Optional[CandidatesData] = None
        self._curriculum_cache: Optional[CurriculumData] = None

    # ============================================================
    # Internal JSON Loading
    # ============================================================

    @staticmethod
    def _load_json(file_path: Path) -> Dict:
        """
        Load a JSON file and return its parsed dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is invalid or the root is not an object.
        """

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required JSON file not found: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Expected a file but found something else: {file_path}"
            )

        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in file '{file_path}': {exc}"
            ) from exc
        except OSError as exc:
            raise OSError(
                f"Could not read file '{file_path}': {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Expected JSON object at root of '{file_path}', "
                f"but received {type(data).__name__}."
            )

        return data

    # ============================================================
    # Load Candidates
    # ============================================================

    def load_candidates(self, force_reload: bool = False) -> CandidatesData:
        """
        Load and validate candidates.json.

        Returns:
            CandidatesData: Validated candidate data.
        """

        if self._candidates_cache is not None and not force_reload:
            return self._candidates_cache

        data = self._load_json(self.candidates_path)

        try:
            candidates_data = CandidatesData(**data)
        except Exception as exc:
            raise ValueError(
                f"Candidate data does not match the expected schema: {exc}"
            ) from exc

        self._candidates_cache = candidates_data
        return candidates_data

    # ============================================================
    # Load Curriculum
    # ============================================================

    def load_curriculum(self, force_reload: bool = False) -> CurriculumData:
        """
        Load and validate curriculum.json.

        Returns:
            CurriculumData: Validated curriculum data.
        """

        if self._curriculum_cache is not None and not force_reload:
            return self._curriculum_cache

        data = self._load_json(self.curriculum_path)

        try:
            curriculum_data = CurriculumData(**data)
        except Exception as exc:
            raise ValueError(
                f"Curriculum data does not match the expected schema: {exc}"
            ) from exc

        self._curriculum_cache = curriculum_data
        return curriculum_data

    # ============================================================
    # Candidate Retrieval
    # ============================================================

    def get_candidate(
        self,
        candidate_id: str,
    ) -> Optional[CandidateProfile]:
        """
        Retrieve a candidate using the exact member.id.

        Args:
            candidate_id: Candidate/member ID.

        Returns:
            CandidateProfile if found, otherwise None.
        """

        if not candidate_id:
            return None

        candidates_data = self.load_candidates()

        for candidate in candidates_data.candidates:
            if candidate.member.id == candidate_id:
                return candidate

        return None

    # ============================================================
    # Curriculum Day Retrieval
    # ============================================================

    def get_curriculum_day(
        self,
        day: int,
    ) -> Optional[CurriculumDay]:
        """
        Retrieve one curriculum day using its day number.

        Args:
            day: Curriculum day number.

        Returns:
            CurriculumDay if found, otherwise None.
        """

        curriculum_data = self.load_curriculum()

        for curriculum_day in curriculum_data.days:
            if curriculum_day.day == day:
                return curriculum_day

        return None

    # ============================================================
    # Multiple Curriculum Days
    # ============================================================

    def get_curriculum_days(
        self,
        days: List[int],
    ) -> List[CurriculumDay]:
        """
        Retrieve multiple curriculum days.

        Invalid or unavailable day numbers are ignored.

        The returned list follows the order of the curriculum data.
        """

        if not days:
            return []

        requested_days: Set[int] = set(days)
        curriculum_data = self.load_curriculum()

        return [
            curriculum_day
            for curriculum_day in curriculum_data.days
            if curriculum_day.day in requested_days
        ]

    # ============================================================
    # Candidate Progress
    # ============================================================

    def get_completed_days(
        self,
        candidate: CandidateProfile,
    ) -> List[int]:
        """
        Return curriculum days whose missions were successfully passed.

        A mission is considered completed only when:
            passed == True
            AND
            skipped != True

        This deliberately does not treat missing 'passed' as True.
        """

        completed_days: List[int] = []

        for mission in candidate.missions:
            if mission.passed is True and mission.skipped is not True:
                completed_days.append(mission.day)

        return sorted(set(completed_days))

    def get_skipped_days(
        self,
        candidate: CandidateProfile,
    ) -> List[int]:
        """
        Return curriculum days explicitly marked as skipped.
        """

        skipped_days: List[int] = []

        for mission in candidate.missions:
            if mission.skipped is True:
                skipped_days.append(mission.day)

        return sorted(set(skipped_days))

    def get_attempted_days(
        self,
        candidate: CandidateProfile,
    ) -> List[int]:
        """
        Return curriculum days for which the candidate has a mission record.

        A mission record is considered attempted even if it was not passed.
        """

        attempted_days: List[int] = []

        for mission in candidate.missions:
            if mission.attempts is not None and mission.attempts > 0:
                attempted_days.append(mission.day)

        return sorted(set(attempted_days))

    # ============================================================
    # Candidate Learning Context
    # ============================================================

    def get_candidate_learning_context(
        self,
        candidate: CandidateProfile,
    ) -> Dict:
        """
        Build a compact learning context for the interview planner.

        This contains candidate progress information but does not
        generate interview questions.
        """

        completed_days = self.get_completed_days(candidate)
        skipped_days = self.get_skipped_days(candidate)
        attempted_days = self.get_attempted_days(candidate)

        return {
            "candidate_id": candidate.member.id,
            "candidate_name": candidate.member.name,
            "job_role": candidate.member.jobRole,
            "years_experience": candidate.member.yearsExperience,
            "education": candidate.member.education,
            "status": candidate.member.status,
            "completed_days": completed_days,
            "skipped_days": skipped_days,
            "attempted_days": attempted_days,
            "signals": (
                candidate.signals.model_dump()
                if candidate.signals is not None
                and hasattr(candidate.signals, "model_dump")
                else (
                    candidate.signals.dict()
                    if candidate.signals is not None
                    else None
                )
            ),
        }

    # ============================================================
    # Relevant Curriculum Retrieval
    # ============================================================

    def get_relevant_curriculum(
        self,
        candidate: CandidateProfile,
        exclude_days: Optional[List[int]] = None,
    ) -> List[CurriculumDay]:
        """
        Retrieve curriculum days relevant to a candidate.

        Priority:
            1. Completed days
            2. Attempted but not completed days

        Skipped days are excluded because they should not be treated
        as completed learning.

        Args:
            candidate: Candidate profile.
            exclude_days: Days already covered by the interview.

        Returns:
            List of relevant CurriculumDay objects.
        """

        exclude: Set[int] = set(exclude_days or [])

        completed_days = self.get_completed_days(candidate)
        attempted_days = self.get_attempted_days(candidate)
        skipped_days = set(self.get_skipped_days(candidate))

        priority_days: List[int] = []

        # First priority: completed learning.
        for day in completed_days:
            if day not in exclude and day not in skipped_days:
                priority_days.append(day)

        # Second priority: attempted but not completed.
        for day in attempted_days:
            if (
                day not in exclude
                and day not in skipped_days
                and day not in priority_days
            ):
                priority_days.append(day)

        return self.get_curriculum_days(priority_days)

    # ============================================================
    # Curriculum Search
    # ============================================================

    def search_curriculum(
        self,
        query: str,
        candidate: Optional[CandidateProfile] = None,
        exclude_days: Optional[List[int]] = None,
    ) -> List[CurriculumDay]:
        """
        Search curriculum days using title, tools, and objectives.

        If a candidate is supplied, only curriculum days relevant to
        that candidate's learning progress are considered.

        Matching is case-insensitive and uses simple token matching.
        """

        if not query or not query.strip():
            return []

        normalized_query = query.lower().strip()
        query_tokens = {
            token
            for token in normalized_query.replace(",", " ").split()
            if token
        }

        if candidate is not None:
            curriculum_days = self.get_relevant_curriculum(
                candidate=candidate,
                exclude_days=exclude_days,
            )
        else:
            curriculum_days = self.load_curriculum().days

        results: List[CurriculumDay] = []

        for curriculum_day in curriculum_days:
            searchable_text = " ".join(
                [
                    curriculum_day.title,
                    curriculum_day.type,
                    " ".join(curriculum_day.tools),
                    " ".join(curriculum_day.objectives),
                ]
            ).lower()

            if normalized_query in searchable_text:
                results.append(curriculum_day)
                continue

            if any(token in searchable_text for token in query_tokens):
                results.append(curriculum_day)

        return results

    # ============================================================
    # Interview Context Retrieval
    # ============================================================

    def get_interview_context(
        self,
        candidate_id: str,
        covered_days: Optional[List[int]] = None,
    ) -> Optional[Dict]:
        """
        Return the candidate and curriculum information required
        by the interview planner.

        This method does not maintain conversation state itself.
        Conversation state belongs to the interview/application layer.
        """

        candidate = self.get_candidate(candidate_id)

        if candidate is None:
            return None

        covered = covered_days or []

        relevant_curriculum = self.get_relevant_curriculum(
            candidate=candidate,
            exclude_days=covered,
        )

        return {
            "candidate": candidate,
            "candidate_learning": self.get_candidate_learning_context(
                candidate
            ),
            "relevant_curriculum": relevant_curriculum,
            "covered_days": sorted(set(covered)),
        }