{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  # https://devenv.sh/basics/
  env.BARENTSWATCH_API_TOKEN = config.secretspec.secrets.BARENTSWATCH_AIS_TOKEN or "";

  # https://devenv.sh/packages/
  packages = [pkgs.git pkgs.secretspec];

  enterShell = ''
    BARENTSWATCH_AIS_TOKEN="$(curl -X POST https://id.barentswatch.no/connect/token \
       -H 'Content-Type: application/x-www-form-urlencoded' \
       --data-urlencode 'client_id=safenein@cavernum.ovh:nova' \
       --data-urlencode "client_secret=$(pass show barents_watch/api)" \
       --data-urlencode 'scope=ais' \
       --data-urlencode 'grant_type=client_credentials' | jq -r '.access_token')"
    export BARENTSWATCH_AIS_TOKEN
  '';

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    package = pkgs.python314;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  # https://devenv.sh/services/
  services.nats.enable = true;
  # processes = {
  #   "norway-api-emitter:dev".exec = "ls *.py | entr 'uv run main.py'";
  # };

  # https://devenv.sh/tasks/
  tasks = {
    "norway-api-emitter:setup".exec = "uv sync";
    "norway-api-emitter:run".exec = "uv run main.py";
  };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    uv run pytest
  '';
}
