"""
Creates clean ZIP archive for hackathon submission.
Excludes venv, .git, and cache directories.
"""

from pathlib import Path
import zipfile

def create_zip():
    root = Path(".")
    zip_path = Path("submission_interview_agent.zip")
    ignore = {"venv", ".git", "__pycache__", ".pytest_cache", "submission_interview_agent.zip"}
    
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for p in root.rglob("*"):
            if any(part in ignore for part in p.parts):
                continue
            if p.is_file():
                zipf.write(p, p.relative_to(root))
                file_count += 1
                
    print(f"Successfully created submission package: {zip_path.resolve()}")
    print(f"Total files included: {file_count}")

if __name__ == "__main__":
    create_zip()
