# let
#   nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-unstable";
#   pkgs = import nixpkgs { config = {}; overlays = []; };
# in
{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell
# pkgs.mkShellNoCC
{
  nativeBuildInputs = with pkgs; [
  ];
  buildInputs = with pkgs; [
  ];
  packages = with pkgs; [
    #(python310.withPackages (ps:
    #  with ps; [
    #    flask
    #    fuzzywuzzy
    #    markdown2
    #python-dotenv
    #  ]))
    #yq-go
    #go-task
    #fzf
  ];
  shellHook =
    /*
    bash
    */
    ''
      pip install uv
      source .venv/bin/activate
      uv pip install -r requirements
      doit
    '';
}
