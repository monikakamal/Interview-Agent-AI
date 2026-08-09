"""
Data loader and semantic chunker for Curriculum and Candidate data.
"""

import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from models.schemas import CandidateProfile, CandidatesData, CurriculumData, CurriculumDay
from utils.logger import logger


class CurriculumChunk(BaseModel):
    """
    Represents a searchable semantic chunk of the curriculum.
    """

    chunk_id: str
    day: int
    module_n: Optional[int] = None
    module_title: Optional[str] = None
    day_title: str
    chunk_type: str  # "objective", "tool", "overview", "full"
    content: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class DataLoader:
    """
    Loads JSON data files and performs semantic chunking of curriculum content.
    """

    def __init__(self, candidates_path: Path, curriculum_path: Path) -> None:
        self.candidates_path = candidates_path
        self.curriculum_path = curriculum_path

    def load_raw_json(self, file_path: Path) -> Dict:
        """Reads and parses JSON file cleanly."""
        if not file_path.exists():
            logger.error(f"JSON file not found at path: '{file_path}'")
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.error(f"Root JSON at '{file_path}' must be a dictionary, got {type(data)}")
                raise ValueError(f"Root JSON must be an object: {file_path}")
            return data
        except Exception as exc:
            logger.error(f"Failed to read/parse JSON from '{file_path}': {exc}\n{traceback.format_exc()}")
            raise

    def load_candidates(self) -> CandidatesData:
        try:
            data = self.load_raw_json(self.candidates_path)
            return CandidatesData(**data)
        except Exception as exc:
            logger.error(f"Candidate loading failed from '{self.candidates_path}': {exc}\n{traceback.format_exc()}")
            raise

    def load_curriculum(self) -> CurriculumData:
        try:
            data = self.load_raw_json(self.curriculum_path)
            return CurriculumData(**data)
        except Exception as exc:
            logger.error(f"Curriculum loading failed from '{self.curriculum_path}': {exc}\n{traceback.format_exc()}")
            raise

    def get_candidate_by_id(self, candidate_id: str) -> Optional[CandidateProfile]:
        try:
            candidates_data = self.load_candidates()
            for candidate in candidates_data.candidates:
                if candidate.member.id == candidate_id:
                    return candidate
            logger.warning(f"get_candidate_by_id(): Candidate ID '{candidate_id}' not found among {len(candidates_data.candidates)} candidates.")
            return None
        except Exception as exc:
            logger.error(f"get_candidate_by_id() failed for '{candidate_id}': {exc}\n{traceback.format_exc()}")
            return None

    def chunk_curriculum(self) -> List[CurriculumChunk]:
        """
        Chunks the curriculum into semantic segments for RAG retrieval.
        Creates chunks for:
        1. Individual objectives for fine-grained retrieval.
        2. Tool sets per day.
        3. Full day overview context.
        """
        curriculum = self.load_curriculum()
        chunks: List[CurriculumChunk] = []

        # Map day to module
        day_to_module: Dict[int, Dict[str, str]] = {}
        for mod in curriculum.modules:
            for d in mod.days:
                day_to_module[d] = {"n": str(mod.n), "title": mod.title}

        for day_data in curriculum.days:
            day_num = day_data.day
            mod_info = day_to_module.get(day_num, {"n": "0", "title": "General"})
            mod_n = int(mod_info["n"])
            mod_title = mod_info["title"]

            # Chunk 1: Day Overview
            tools_str = ", ".join(day_data.tools) if day_data.tools else "None"
            objs_str = "; ".join(day_data.objectives) if day_data.objectives else "None"
            overview_text = (
                f"Curriculum Day {day_num}: {day_data.title} ({day_data.type}). "
                f"Module: {mod_title}. Tools: {tools_str}. Key Objectives: {objs_str}."
            )
            chunks.append(
                CurriculumChunk(
                    chunk_id=f"day_{day_num}_overview",
                    day=day_num,
                    module_n=mod_n,
                    module_title=mod_title,
                    day_title=day_data.title,
                    chunk_type="overview",
                    content=overview_text,
                    metadata={
                        "day": str(day_num),
                        "type": day_data.type,
                        "title": day_data.title,
                    },
                )
            )

            # Chunk 2: Individual Objectives
            for idx, obj in enumerate(day_data.objectives):
                chunks.append(
                    CurriculumChunk(
                        chunk_id=f"day_{day_num}_obj_{idx+1}",
                        day=day_num,
                        module_n=mod_n,
                        module_title=mod_title,
                        day_title=day_data.title,
                        chunk_type="objective",
                        content=f"Day {day_num} ({day_data.title}) Objective: {obj}",
                        metadata={"day": str(day_num), "objective": obj},
                    )
                )

            # Chunk 3: Tools & Technical Stack
            if day_data.tools:
                chunks.append(
                    CurriculumChunk(
                        chunk_id=f"day_{day_num}_tools",
                        day=day_num,
                        module_n=mod_n,
                        module_title=mod_title,
                        day_title=day_data.title,
                        chunk_type="tool",
                        content=f"Day {day_num} ({day_data.title}) Tooling and Stack: {tools_str}",
                        metadata={"day": str(day_num), "tools": tools_str},
                    )
                )

        return chunks
