import hashlib
import re
import shlex
from pathlib import Path

from qlever.command import QleverCommand
from qlever.log import log
from qlever.util import run_command


def _image_tag(branch: str) -> str:
    """Return a valid, collision-resistant Docker tag for a Git branch."""
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).lstrip(".-")
    if sanitized == branch and len(sanitized) <= 128:
        return sanitized

    sanitized = sanitized or "branch"
    digest = hashlib.sha256(branch.encode()).hexdigest()[:12]
    return f"{sanitized[:115]}-{digest}"


class VisualizeCommand(QleverCommand):
    def __init__(self):
        pass

    def description(self) -> str:
        return "Visualize SPARQL conformance test results."

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str, list[str]]:
        return {"runtime": ["system"],
                "conformance_ui": ["result_directory", "port", "ui_branch"]
                }

    def additional_arguments(self, subparser):
        pass

    def execute(self, args) -> bool:
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        system = args.system
        result_dir = (
            Path.cwd() if args.result_directory == "$(pwd)"
            else Path(args.result_directory).resolve()
        )
        port = args.port
        branch = args.ui_branch
        image_tag = _image_tag(branch)

        compose_cmd = (
            f"LOCAL_RESULTS_DIR={shlex.quote(str(result_dir))} "
            f"PRIVATE_WEB_PORT={shlex.quote(str(port))} "
            f"SPARQL_CONFORMANCE_UI_BRANCH={shlex.quote(branch)} "
            f"SPARQL_CONFORMANCE_UI_IMAGE_TAG={shlex.quote(image_tag)} "
            f"{system} compose -f {shlex.quote(str(compose_file))}"
        )

        # Private mode keeps its database in the API container, so recreating the
        # Compose project guarantees a clean import of the selected result files.
        run_command(f"{compose_cmd} down", show_stderr=True)

        # Resolve the branch on every invocation. Docker still reuses unchanged
        # layers, but a moving branch such as `main` can no longer leave the user
        # on an indefinitely stale UI image.
        log.info(
            f"Building sparql-conformance-ui images from branch '{branch}' "
            "(unchanged layers will be cached)..."
        )
        try:
            run_command(f"{compose_cmd} build --pull", show_output=True)
        except Exception as e:
            log.error(f"Building the images failed: {e}")
            return False

        log.info(f"Starting visualization at http://localhost:{port}")
        try:
            run_command(f"{compose_cmd} up", show_output=True)
        except Exception as e:
            log.error(f"Starting visualization failed: {e}")
            return False
        finally:
            run_command(f"{compose_cmd} down", show_stderr=True)

        return True
