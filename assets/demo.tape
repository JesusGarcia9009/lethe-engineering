# Generate the demo GIF headlessly with VHS (https://github.com/charmbracelet/vhs):
#
#     vhs assets/demo.tape
#
# Produces assets/lethe-demo.gif. Requires: vhs + ffmpeg + ttyd, and the package
# installed in the active environment (pip install -e . from the repo root).

Output assets/lethe-demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 760
Set Padding 24
Set Theme "Dracula"
Set TypingSpeed 60ms

Hide
Type "python -m lethe.examples.mcp_demo"
Enter
Show

# The demo paces itself with short internal pauses (~8s total); wait it out.
Sleep 12s
