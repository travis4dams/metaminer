# GitHub Actions Workflows

## PyPI Publishing Workflow

The `publish-to-pypi.yml` workflow automates the process of testing, building, and publishing the metaminer package to PyPI.

### Features

- **Multi-Python Testing**: Tests the package on Python 3.8-3.12
- **Version Validation**: Ensures version consistency between `pyproject.toml` and `__init__.py`
- **Secure Publishing**: Uses OpenID Connect (OIDC) trusted publishing (no API tokens needed)
- **Test PyPI Support**: Allows testing releases on Test PyPI before production
- **Automatic Releases**: Creates GitHub releases with build artifacts
- **Manual Triggers**: Supports manual workflow dispatch for testing

### Trigger Conditions

#### Automatic Triggers
- **Production Release**: Push a version tag (e.g., `v0.3.1`)
- **Test Release**: Push a release candidate tag (e.g., `v0.3.1-rc1`)

#### Manual Triggers
- Go to Actions → Publish to PyPI → Run workflow
- Choose environment: `testpypi` or `pypi`

### Setup Requirements

#### 1. Configure Trusted Publishing on PyPI

**For Production PyPI:**
1. Go to https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher:
   - PyPI Project Name: `metaminer`
   - Owner: `travis4dams`
   - Repository name: `metaminer`
   - Workflow name: `publish-to-pypi.yml`
   - Environment name: `pypi`

**For Test PyPI:**
1. Go to https://test.pypi.org/manage/account/publishing/
2. Add a new trusted publisher with the same settings but:
   - Environment name: `testpypi`

#### 2. Configure GitHub Environments

**Create Production Environment:**
1. Go to Settings → Environments → New environment
2. Name: `pypi`
3. Add protection rules (recommended):
   - Required reviewers: Add yourself
   - Restrict to protected branches: `main`

**Create Test Environment:**
1. Go to Settings → Environments → New environment
2. Name: `testpypi`
3. No protection rules needed for testing

### Usage Examples

#### Publishing a New Version

1. **Update version numbers:**
   ```bash
   # Update both files to the same version
   # pyproject.toml: version = "0.3.1"
   # metaminer/__init__.py: __version__ = "0.3.1"
   ```

2. **Commit and push changes:**
   ```bash
   git add .
   git commit -m "Bump version to 0.3.1"
   git push origin main
   ```

3. **Create and push a tag:**
   ```bash
   git tag v0.3.1
   git push origin v0.3.1
   ```

4. **Monitor the workflow:**
   - Go to Actions tab in GitHub
   - Watch the "Publish to PyPI" workflow run
   - Check for any failures and address them

#### Testing a Release

1. **Create a release candidate tag:**
   ```bash
   git tag v0.3.1-rc1
   git push origin v0.3.1-rc1
   ```

2. **Or use manual dispatch:**
   - Go to Actions → Publish to PyPI → Run workflow
   - Select `testpypi` environment
   - Click "Run workflow"

3. **Test the package from Test PyPI:**
   ```bash
   pip install -i https://test.pypi.org/simple/ metaminer==0.3.1rc1
   ```

### Workflow Jobs

1. **Test**: Runs tests across Python 3.8-3.12
2. **Build**: Creates wheel and source distributions
3. **Publish-TestPyPI**: Publishes to Test PyPI (for RC tags or manual dispatch)
4. **Publish-PyPI**: Publishes to production PyPI (for release tags)
5. **Create-Release**: Creates GitHub release with artifacts

### Troubleshooting

#### Common Issues

**Version Mismatch Error:**
- Ensure `pyproject.toml` and `metaminer/__init__.py` have the same version
- Check that the git tag matches the package version (without 'v' prefix)

**Trusted Publishing Failed:**
- Verify trusted publisher configuration on PyPI
- Check that environment names match exactly
- Ensure the workflow file path is correct

**Tests Failed:**
- Fix any failing tests before publishing
- The workflow will continue even if tests fail, but this is not recommended

**Permission Denied:**
- Check that the repository has the correct permissions
- Verify that environments are configured properly
- Ensure you have admin access to the repository

#### Manual Recovery

If a workflow fails partway through:

1. **Fix the issue** (code, configuration, etc.)
2. **Delete the problematic tag** (if it was a tag trigger):
   ```bash
   git tag -d v0.3.1
   git push origin :refs/tags/v0.3.1
   ```
3. **Re-run** the workflow or create a new tag

### Security Notes

- This workflow uses OIDC trusted publishing, which is more secure than API tokens
- No secrets need to be stored in the repository
- Each environment can have different protection rules
- All publishing actions are logged and auditable
