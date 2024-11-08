Output "grummage.gif"
Require grype
Require bash
Require figlet
Set Shell "bash"
Set FontFamily "Iosevka Term"
Set FontSize 14
Set Width 800
Set Height 600
Set Padding 4
Set WindowBar Colorful
#Set WindowBar Rings
Set Theme catppuccin-macchiato
Set Margin 8
Set MarginFill "#0f40c0"
Set BorderRadius 10
Set Framerate 60
Set PlaybackSpeed 1
Env PS1 "[0;38;5;231;48;5;31;1m popey [0;38;5;31;48;5;240;22m [0;38;5;252;48;5;240;1m~ [0;38;5;240;49;22m [0m"
Sleep 250ms
Type `figlet Grummage`
Enter
Sleep 1s
Type@5ms `./grummage ./example_sboms/nextcloud-latest-syft-sbom.json`
Sleep 500ms
Enter
Sleep 3s
Enter
Sleep 3s
Type "v"
Sleep 3s
Type "t"
Sleep 3s
Down
Sleep 50ms
Down
Sleep 50ms
Down
Sleep 3s
Enter
Sleep 3s
Down
Sleep 50ms
Enter
Sleep 50ms
Down
Sleep 50ms
Enter
Sleep 5s
Up 6
Type "s"
Sleep 3s
Down 1
Sleep 2s
Enter
Sleep 2s
Down
Enter
Sleep 2
Type "e"
Sleep 2s
Screenshot grummage.png
Sleep 3s
Type "q"
Sleep 2s
