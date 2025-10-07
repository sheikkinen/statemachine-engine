# Release Process

This document describes how to create a new release of statemachine-engine.

## Prerequisites

1. Ensure all tests pass: `pytest tests/ -v`
2. Update version in `pyproject.toml`
3. Update `CHANGELOG.md` with release notes
4. Commit all changes: `git commit -am "Prepare v1.0.0 release"`
5. Push to GitHub: `git push origin main`

## Creating a Release

### Automated Release (Recommended)

1. **Create and push a version tag:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **GitHub Actions will automatically:**
   - Run tests on Python 3.9, 3.10, 3.11, 3.12
   - Build the package (wheel + source distribution)
   - Publish to PyPI (requires PyPI trusted publishing setup)
   - Create a GitHub Release with artifacts

3. **Verify the release:**
   - Check GitHub Actions: https://github.com/sheikkinen/statemachine-engine/actions
   - Check PyPI: https://pypi.org/project/statemachine-engine/
   - Check GitHub Releases: https://github.com/sheikkinen/statemachine-engine/releases

### Manual Release (Fallback)

If automated release fails or for testing:

```bash
# 1. Build the package
python -m build

# 2. Check the built package
twine check dist/*

# 3. Upload to TestPyPI (optional, for testing)
twine upload --repository testpypi dist/*

# 4. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ statemachine-engine

# 5. Upload to PyPI
twine upload dist/*

# 6. Create GitHub Release manually
# Go to: https://github.com/sheikkinen/statemachine-engine/releases/new
# - Tag: v1.0.0
# - Title: v1.0.0
# - Description: Copy from CHANGELOG.md
# - Attach: dist/*.whl and dist/*.tar.gz
```

## PyPI Trusted Publishing Setup

To enable automated PyPI publishing from GitHub Actions:

1. **Go to PyPI project settings:**
   - https://pypi.org/manage/project/statemachine-engine/settings/publishing/

2. **Add trusted publisher:**
   - PyPI Project Name: `statemachine-engine`
   - Owner: `sheikkinen`
   - Repository name: `statemachine-engine`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

3. **No API tokens needed!** GitHub Actions uses OIDC authentication.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

Examples:
- `v1.0.0` - Initial stable release
- `v1.0.1` - Bug fix
- `v1.1.0` - New feature (e.g., new built-in action)
- `v2.0.0` - Breaking change (e.g., API change)

## Pre-release Versions

For testing:
- Alpha: `v1.0.0a1`, `v1.0.0a2`
- Beta: `v1.0.0b1`, `v1.0.0b2`
- Release Candidate: `v1.0.0rc1`, `v1.0.0rc2`

## Post-Release Checklist

- [ ] Verify package on PyPI
- [ ] Test installation: `pip install statemachine-engine`
- [ ] Verify GitHub Release created
- [ ] Update documentation if needed
- [ ] Announce release (if applicable)
- [ ] Start next development cycle (bump version to next .dev0)

## Hotfix Process

For urgent fixes to released version:

1. Create hotfix branch from tag: `git checkout -b hotfix/v1.0.1 v1.0.0`
2. Make fixes and test
3. Update version to `1.0.1`
4. Update CHANGELOG.md
5. Merge to main: `git checkout main && git merge hotfix/v1.0.1`
6. Tag and release: `git tag v1.0.1 && git push origin v1.0.1`

## Troubleshooting

### Release workflow fails
- Check GitHub Actions logs
- Verify PyPI trusted publishing is configured
- Ensure tests pass locally: `pytest tests/ -v`
- Check version number format: `vX.Y.Z`

### PyPI upload fails
- Verify package name not taken
- Check twine output: `twine check dist/*`
- Try TestPyPI first: `twine upload --repository testpypi dist/*`

### Package import fails after install
- Check MANIFEST.in includes all necessary files
- Verify package structure: `pip show -f statemachine-engine`
- Test in clean environment: `python -m venv test_env && source test_env/bin/activate`
