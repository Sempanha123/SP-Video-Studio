pragma Singleton
import QtQuick 2.15
QtObject {
    id: root
    property string mode: "system"
    property string density: "comfortable"
    property bool reducedMotion: false
    property string interfaceTextSize: "default"
    property bool strongerFocus: false
    readonly property bool compact: density === "compact"
    readonly property real densityScale: compact ? 0.88 : 1.0
    readonly property real textScale: interfaceTextSize === "large" ? 1.12 : 1.0
    readonly property bool systemDark: (systemPalette.window.r + systemPalette.window.g + systemPalette.window.b) / 3 < 0.5
    readonly property bool darkMode: mode === "dark" || (mode === "system" && systemDark)
    readonly property Colors colors: Colors { darkMode: root.darkMode }
    readonly property Typography type: Typography { scale: root.textScale }
    readonly property Spacing spacing: Spacing {}
    readonly property Radius radius: Radius {}
    readonly property AnimationTokens animation: AnimationTokens { reducedMotion: root.reducedMotion }
    readonly property int focusWidth: strongerFocus ? 3 : 2
    readonly property int tooltipDelay: 550
    readonly property int controlHeightSmall: Math.round((compact ? 26 : 28) * Math.min(1.08, textScale))
    readonly property int controlHeight: Math.round((compact ? 30 : 34) * Math.min(1.08, textScale))
    readonly property int controlHeightLarge: Math.round((compact ? 36 : 40) * Math.min(1.08, textScale))
    function setMode(value) { if (value === "system" || value === "light" || value === "dark") mode = value }
    function setDensity(value) { if (value === "comfortable" || value === "compact") density = value }
    function setAccessibility(reduceMotion, textSize, strongFocus) {
        reducedMotion = !!reduceMotion
        if (textSize === "default" || textSize === "large") interfaceTextSize = textSize
        strongerFocus = !!strongFocus
    }
    readonly property SystemPalette systemPalette: SystemPalette {}
}
