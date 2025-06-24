import argparse
from config_loader import load_repo_config
from github_cli_client import GitHubCLIClient
import logging
from pr_detect_changed_subtrees import parse_arguments, get_valid_prefixes, find_matched_subtrees, output_subtrees
import requests
from typing import List, Optional

logger = logging.getLogger(__name__)

def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Detect changed subtrees in a PR.")
    parser.add_argument("--az-pat", required=True, help="Azure authentication PAT")
    parser.add_argument("--az-request-data-file", required=True, help="Path to the Azure API request data file")
    parser.add_argument("--repo", required=True, help="Full repository name (e.g., org/repo)")
    parser.add_argument("--pr", required=True, type=int, help="Pull request number")
    parser.add_argument("--config", required=False, default=".github/repos-config.json", help="Path to the repos-config.json file")
    parser.add_argument("--require-fanout", action="store_true", help="Only include entries with enable_pr_fanout=true")
    parser.add_argument("--require-auto-pull", action="store_true", help="Only include entries with auto_subtree_pull=true")
    parser.add_argument("--require-auto-push", action="store_true", help="Only include entries with auto_subtree_push=true")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing to GITHUB_OUTPUT.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def kick_off_pipeline(project, az_pat, request_data_file):
    PROJECT_GUID = "b22b20c4-7700-462e-b80b-76b8222eb8f2"
    REPO = "your-repo"
    BASE_URL = f"https://dev.azure.com/ROCm-CI/ROCm-CI/_apis"
    API_VERSION = "7.1"

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {az_pat}"
    }

    DEFINITION_IDS = {
        "projects/rocPRIM": 273,
        "projects/hipCUB": 277,
        "projects/rocThrust": 276,
        "projects/rocRAND": 274,
        "projects/hipRAND": 275,
        "projects/hipBLAS-common": 300,
        "shared/Tensile": 305
    }

    url = f"{BASE_URL}/pipelines/{DEFINITION_IDS.get(project)}/runs?api-version={API_VERSION}"

    with open(request_data_file, 'r') as file:
        data = file.read()

        response = requests.post(url, headers=HEADERS, json=data)

        if response.status_code == 200:
            result = response.json()
            print(f"Pipeline started successfully for {project}: {result['id']}")
            return result
        else:
            print(f"Failed to start pipeline for {project}: {response.text}")
            return None


def main(argv=None) -> None:
    args = parse_arguments(argv)
    logging.basicConfig(
        level = logging.DEBUG if args.debug else logging.INFO
    )
    client = GitHubCLIClient()
    config = load_repo_config(args.config)
    changed_files = client.get_changed_files(args.repo, int(args.pr))
    valid_prefixes = get_valid_prefixes(config, args.require_fanout, args.require_auto_pull, args.require_auto_push)
    matched_subtrees = find_matched_subtrees(changed_files, valid_prefixes)

    for subtree in matched_subtrees:
        print(f"Matched subtree: {subtree}")
        kick_off_pipeline(subtree, args.az_pat, args.az_request_data_file)


if __name__ == "__main__":
    main()
