pragma Singleton
import QtQuick 2.15
QtObject {
    id: root
    property string mode: "system"
    property string density: "comfortable"
    property bool reducedMotion: false
    readonly property bool compact: density === "compact"
    readonly property real densityScale: compact ? 0.88 : 1.0
    readonly property bool systemDark: (systemPalette.window.r + systemPalette.window.g + systemPalette.window.b) / 3 < 0.5
    readonly property bool darkMode: mode === "dark" || (mode === "system" && systemDark)
    readonly property Colors colors: Colors { darkMode: root.darkMode }
    readonly property Typography type: Typography {}
    readonly property Spacing spacing: Spacing {}
    readonly property Radius radius: Radius {}
    readonly property AnimationTokens animation: AnimationTokens { reducedMotion: root.reducedMotion }
    readonly property int controlHeightSmall: compact ? 26 : 28
    readonly property int controlHeight: compact ? 30 : 34
    readonly property int controlHeightLarge: compact ? 36 : 40
    function setMode(value) { if (value === "system" || value === "light" || value === "dark") mode = value }
    function setDensity(value) { if (value === "comfortable" || value === "compact") density = value }
    readonly property SystemPalette systemPalette: SystemPalette {}
}
