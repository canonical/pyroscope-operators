#!/bin/bash
# Pack the worker charm and stage it for use with charmcraft test.
#
# The packed .charm file and the worker's charmcraft.yaml (needed for OCI
# resource lookups) are placed in coordinator/.worker-charm/.  That directory
# is synced to /root/proj/.worker-charm/ inside the spread VM because
# charmcraft test syncs coordinator/ to /root/proj/.
#
# After running this script, `charmcraft test spread/integration/` will
# deploy the locally packed worker charm instead of fetching it from charmhub.
# The .worker-charm/ directory is gitignored; re-run this script whenever the
# worker source changes.

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
COORDINATOR_DIR="$REPO_ROOT/coordinator"
WORKER_DIR="$REPO_ROOT/worker"
STAGING_DIR="$COORDINATOR_DIR/.worker-charm"

echo "==> Staging directory: $STAGING_DIR"
mkdir -p "$STAGING_DIR"

echo "==> Copying worker/charmcraft.yaml for OCI resource lookups"
cp "$WORKER_DIR/charmcraft.yaml" "$STAGING_DIR/charmcraft.yaml"

echo "==> Packing worker charm (output goes to worker/ first)"
cd "$WORKER_DIR"
# charmcraft pack runs inside an LXD container and cannot write directly to an
# absolute host path outside the project root, so pack into the default output
# location (worker/) and then move the resulting file to the staging directory.
charmcraft pack

CHARM_FILE=$(ls -1t pyroscope-worker-k8s_*.charm 2>/dev/null | head -1)
if [ -z "$CHARM_FILE" ]; then
    echo "ERROR: no .charm file found after packing" >&2
    exit 1
fi

echo "==> Moving $CHARM_FILE to staging directory"
mv "$CHARM_FILE" "$STAGING_DIR/"

echo ""
echo "==> Done. Worker charm staged at $STAGING_DIR/"
ls -lh "$STAGING_DIR/"*.charm
echo ""
echo "Run 'charmcraft test spread/integration/' from coordinator/ to use it."
