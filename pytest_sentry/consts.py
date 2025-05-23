_ENVVARS_AS_TAGS = frozenset(
    [
        "GITHUB_WORKFLOW",  # The name of the workflow.
        "GITHUB_RUN_ID",  # A unique number for each run within a repository. This number does not change if you re-run the workflow run.
        "GITHUB_RUN_NUMBER",  # A unique number for each run of a particular workflow in a repository. This number begins at 1 for the workflow's first run, and increments with each new run. This number does not change if you re-run the workflow run.
        "GITHUB_ACTION",  # The unique identifier (id) of the action.
        "GITHUB_ACTOR",  # The name of the person or app that initiated the workflow. For example, octocat.
        "GITHUB_REPOSITORY",  # The owner and repository name. For example, octocat/Hello-World.
        "GITHUB_EVENT_NAME",  # The name of the webhook event that triggered the workflow.
        "GITHUB_EVENT_PATH",  # The path of the file with the complete webhook event payload. For example, /github/workflow/event.json.
        "GITHUB_WORKSPACE",  # The GitHub workspace directory path. The workspace directory is a copy of your repository if your workflow uses the actions/checkout action. If you don't use the actions/checkout action, the directory will be empty. For example, /home/runner/work/my-repo-name/my-repo-name.
        "GITHUB_SHA",  # The commit SHA that triggered the workflow. For example, ffac537e6cbbf934b08745a378932722df287a53.
        "GITHUB_REF",  # The branch or tag ref that triggered the workflow. For example, refs/heads/feature-branch-1. If neither a branch or tag is available for the event type, the variable will not exist.
        "GITHUB_HEAD_REF",  # Only set for pull request events. The name of the head branch.
        "GITHUB_BASE_REF",  # Only set for pull request events. The name of the base branch.
        "GITHUB_SERVER_URL",  # Returns the URL of the GitHub server. For example: https://github.com.
        "GITHUB_API_URL",  # Returns the API URL. For example: https://api.github.com.
        # Gitlab CI variables, as defined here https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        "CI_COMMIT_REF_NAME",  # Branch or tag name
        "CI_JOB_ID",  # Unique job ID
        "CI_JOB_URL",  # Job details URL
        "CI_PIPELINE_ID",  # Unique pipeline ID
        "CI_PROJECT_NAME",
        "CI_PROJECT_PATH",
        "CI_SERVER_URL",
        "GITLAB_USER_NAME",  # The name of the user who started the job.
        # CircleCI variables, as defined here https://circleci.com/docs/variables/#built-in-environment-variables
        "CIRCLE_BRANCH",  # The name of the Git branch currently being built.
        "CIRCLE_BUILD_NUM",  # The number of the current job. Job numbers are unique for each job.
        "CIRCLE_BUILD_URL",  # The URL for the current job on CircleCI.
        "CIRCLE_JOB",  # The name of the current job.
        "CIRCLE_NODE_INDEX",  # For jobs that run with parallelism enabled, this is the index of the current parallel run.
        "CIRCLE_PR_NUMBER",  # The number of the associated GitHub or Bitbucket pull request.
        "CIRCLE_PR_REPONAME",  # The name of the GitHub or Bitbucket repository where the pull request was created.
        "CIRCLE_PR_USERNAME",  # The GitHub or Bitbucket username of the user who created the pull request.
        "CIRCLE_PROJECT_REPONAME",  # The name of the repository of the current project.
        "CIRCLE_PROJECT_USERNAME",  # The GitHub or Bitbucket username of the current project.
        "CIRCLE_PULL_REQUEST",  # The URL of the associated pull request.
        "CIRCLE_REPOSITORY_URL",  # The URL of your GitHub or Bitbucket repository.
        "CIRCLE_SHA1",  # The SHA1 hash of the last commit of the current build.
        "CIRCLE_TAG",  # The name of the git tag, if the current build is tagged.
        "CIRCLE_USERNAME",  # The GitHub or Bitbucket username of the user who triggered the pipeline.
        "CIRCLE_WORKFLOW_ID",  # A unique identifier for the workflow instance of the current job.
        "CIRCLE_WORKFLOW_JOB_ID",  # A unique identifier for the current job.
        "CIRCLE_WORKFLOW_WORKSPACE_ID",  # An identifier for the workspace of the current job.
    ]
)
