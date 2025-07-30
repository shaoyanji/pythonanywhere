# let
#   nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-unstable";
#   pkgs = import nixpkgs { config = {}; overlays = []; };
# in
{pkgs ? import <nixpkgs> {}}: let
  requirements = builtins.readFile ./requirements.txt;
  requirementsList = pkgs.lib.splitString "\n" requirements;
  filteredRequirements = pkgs.lib.filter (pkg: pkg != "") requirementsList;
  pythonPackages = map (pkg: pkgs.python3Packages.${pkg}) filteredRequirements;
in
  pkgs.mkShell
  # pkgs.mkShellNoCC
  {
    nativeBuildInputs = with pkgs; [
    ];
    buildInputs = with pkgs; [
      (python3.withPackages (ps: pythonPackages))
    ];
    packages = with pkgs; [
      # tgpt
      #yq-go
      #go-task
      #fzf
    ];
    # shellHook =
    /*
    bash
    */
    # ''
    # pip install uv
    # source .venv/bin/activate
    # uv pip install -r requirements.txt
    # doit
    # '';
  }
