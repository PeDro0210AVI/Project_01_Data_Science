{

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-25.11";
  };

  outputs =
    {
      nixpkgs,
      ...
    }:
    let
      forAllSystems =
        function:
        nixpkgs.lib.genAttrs
          [
            "x86_64-linux"
            "aarch64-darwin"
          ]
          (
            system:
            let
              pkgs = nixpkgs.legacyPackages.${system};
            in
            function {
              inherit
                pkgs
                ;

            }
          );
    in
    {

      devShells = forAllSystems (
        {
          pkgs,

        }:
        let
          pythonPackages =
            ps: with ps; [
              ipykernel
              jupyterlab-vim
              jupyterlab
              jupyterlab-lsp
              python-lsp-server

              numpy
              pandas
              matplotlib
              scipy
              statsmodels
              scikit-learn
            ];
          pythonEnv = pkgs.python3.withPackages pythonPackages;

        in
        {
          default = pkgs.mkShell {

            packages = [
              pythonEnv
            ];

          };
        }
      );

    };
}
