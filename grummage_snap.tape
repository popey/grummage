Output "grummage_snap.gif"
Output "grummage_snap.mp4"
Require grype
Require bash
Require figlet
Set Shell "bash"
#Set FontFamily "Iosevka Term"
Set FontFamily "BlexMono Nerd Font Mono"
Set FontSize 18
Set Width 1280
Set Height 720
Set Padding 4
Set WindowBar Colorful
#Set WindowBar Rings
Set Theme catppuccin-macchiato
Set Margin 8
Set MarginFill "#0f40c0"
Set BorderRadius 10
Set Framerate 30
Set PlaybackSpeed 1
Env PS1 "[0;38;5;231;48;5;31;1m popey [0;38;5;31;48;5;240;22m [0;38;5;252;48;5;240;1m~ [0;38;5;240;49;22m [0m"
Sleep 50ms
Type@1ms `figlet -c -f jazmine grummage`
Enter
Sleep 100ms
Enter
Sleep 150ms
Type@5ms `./grummage ./example_sboms/nextcloud-latest-syft-sbom.json`
Sleep 500ms
Enter
Sleep 5s
Enter
Sleep 100ms
Down@50ms 5
Sleep 100ms
Enter
Sleep 100ms
Down@50ms 1
Sleep 100ms
Enter
Sleep 100ms
Type "e"
Sleep 5s
Type "s"
Sleep 100ms
PageUp
Sleep 1s
Down@50ms 1
Enter
Down@50ms 10
Enter
Sleep 100ms
Type "e"
Sleep 5s
Type "t"
Sleep 100ms
PageUp
Sleep 1s
Down@50ms 3
Enter
Down@50ms 3
Enter
Down@50ms 1
Enter
Type "e"
Sleep 3s
Enter
Sleep 3s
Screenshot grummage_snap.png
Sleep 3s
Type "q"
Sleep 2s
