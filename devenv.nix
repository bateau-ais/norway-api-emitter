{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  # https://devenv.sh/packages/
  packages = [ pkgs.git ];

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
