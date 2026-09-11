pragma Singleton
import QtQuick 2.15

QtObject {
    id: root
    property string mode: "system"
    readonly property bool systemDark: (systemPalette.window.r + systemPalette.window.g + systemPalette.window.b) / 3 < 0.5
    readonly property bool darkMode: mode === "dark" || (mode === "system" && systemDark)

    readonly property Colors colors: Colors { darkMode: root.darkMode }
    readonly property Typography type: Typography {}
    readonly property Spacing spacing: Spacing {}
    readonly property Radius radius: Radius {}
    readonly property AnimationTokens animation: AnimationTokens {}

    function setMode(value) {
        if (value === "system" || value === "light" || value === "dark")
            mode = value
    }

    readonly property SystemPalette systemPalette: SystemPalette {}
}
