#!/usr/bin/env bash

pushd "$(dirname "$0")" >/dev/null

git clean -dxfe .idea
rm bene.tgz 2>/dev/null
src="$(basename "$(dirname "$(readlink -f "$0")")")"
echo "Packaging $src..."
cd ..
tar --exclude '.*' -czvf bene.tgz "$src"

popd >/dev/null

