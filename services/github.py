import subprocess
from pathlib import Path
import shutil
from typing import List, Dict

repos_dir = Path("/tmp/repos")

SUPPORTED_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.go': 'go',
    '.rs': 'rust',
    '.md': 'markdown',
}

IGNORE_DIRS = {
    '.git',
    'node_modules',
    '__pycache__',
    'venv',
    'myenv',
    '.env',
    'dist',
    'build',
    '.idea',
    '.vscode'
}

def clone_repo(repo_name: str, repo_url: str) -> None:

    repos_dir.mkdir(parents=True, exist_ok=True)
    repo_path = repos_dir / repo_name

    if repo_path.exists():
        shutil.rmtree(repo_path)
    
    result = subprocess.run(
        ["git", "clone", repo_url, str(repo_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Git clone failed: {result.stderr}")
    
    return repo_path

def get_code_files(repo_path: Path) -> List[Dict[str, str]]:

    code_files = []
    
    for file_path in repo_path.rglob('*'):
        
        if not file_path.is_file():
            continue
        
        if any(ignored in file_path.parts for ignored in IGNORE_DIRS):
            continue
        
        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8')

        except Exception:
            continue
        
        if not content.strip():
            continue
        
        code_files.append({
            "path": str(file_path.relative_to(repo_path)),
            "content": content,
            "language": SUPPORTED_EXTENSIONS[file_path.suffix]
        })
    
    return code_files


def cleanup_repo(repo_path: Path) -> None:

    if repo_path.exists():
        shutil.rmtree(repo_path)

    