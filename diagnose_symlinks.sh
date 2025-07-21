#!/bin/bash
# Diagnose symlink and permission issues with OpenGrok

echo "🔍 Diagnosing OpenGrok Symlink Issues"
echo "====================================="

echo -e "\n1. Checking workspace directory:"
ls -la ~/.codemcp/opengrok-workspace/

echo -e "\n2. Checking if symlinks resolve:"
for link in ~/.codemcp/opengrok-workspace/*; do
    if [ -L "$link" ]; then
        target=$(readlink "$link")
        echo -n "$(basename $link) -> $target "
        if [ -e "$target" ]; then
            echo "✅ (exists)"
        else
            echo "❌ (broken)"
        fi
    fi
done

echo -e "\n3. Testing Docker access to symlinks:"
docker run --rm -v ${HOME}/.codemcp/opengrok-workspace:/test alpine sh -c "
echo 'Contents of /test:'
ls -la /test/
echo ''
echo 'Testing symlink resolution:'
for dir in /test/*; do
    echo -n \"\$(basename \$dir): \"
    if [ -d \"\$dir\" ]; then
        echo 'Directory accessible ✅'
    else
        echo 'Not accessible ❌'
    fi
done
"

echo -e "\n4. Docker Desktop settings check:"
echo "Make sure Docker Desktop has access to these paths:"
echo "- $HOME/.codemcp"
echo "- /Users/mustafaacar/retter"
echo "- /Users/mustafaacar/codemcp"

echo -e "\n5. Alternative solution - bind mount real directories:"
echo "Instead of using symlinks, we could directly mount the projects."
echo "This would require a different approach in docker-compose.yml"
