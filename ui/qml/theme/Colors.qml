import QtQuick 2.15
QtObject {
    property bool darkMode: false

    readonly property color background: darkMode ? "#17181D" : "#F7F7FA"
    readonly property color surface: darkMode ? "#1E2026" : "#FFFFFF"
    readonly property color surfaceRaised: darkMode ? "#252830" : "#FCFCFE"
    readonly property color surfaceHover: darkMode ? "#292C35" : "#F2F1F7"
    readonly property color surfacePressed: darkMode ? "#30333D" : "#ECEAF3"
    readonly property color surfaceSelected: darkMode ? "#302F45" : "#F0EDFA"
    readonly property color elevated: darkMode ? "#292C34" : "#FFFFFF"
    readonly property color sidebar: darkMode ? "#1A1C21" : "#FBFAFD"

    readonly property color border: darkMode ? "#30333B" : "#E5E3EB"
    readonly property color borderStrong: darkMode ? "#424650" : "#D3CFDC"
    readonly property color focus: darkMode ? "#A89AE1" : "#7768B5"

    readonly property color textPrimary: darkMode ? "#F1F0F5" : "#25232B"
    readonly property color textSecondary: darkMode ? "#BBB8C4" : "#615D6A"
    readonly property color textMuted: darkMode ? "#8D8996" : "#8C8795"
    readonly property color textDisabled: darkMode ? "#64616B" : "#B3AFB9"
    readonly property color onAccent: "#FFFFFF"
    readonly property color overlayScrim: darkMode ? "#990E0F12" : "#6623212B"

    readonly property color accent: darkMode ? "#9789D2" : "#7567B1"
    readonly property color accentHover: darkMode ? "#A496DC" : "#8173BD"
    readonly property color accentPressed: darkMode ? "#887BC2" : "#685B9F"
    readonly property color accentSoft: darkMode ? "#302D45" : "#F0EDFA"

    readonly property color success: darkMode ? "#77B79A" : "#4A8B70"
    readonly property color successSoft: darkMode ? "#24372F" : "#ECF6F1"
    readonly property color warning: darkMode ? "#D0AD70" : "#A87931"
    readonly property color warningSoft: darkMode ? "#3C3426" : "#FBF4E8"
    readonly property color danger: darkMode ? "#D9858D" : "#B85C65"
    readonly property color dangerSoft: darkMode ? "#402B2E" : "#F9ECEE"
    readonly property color info: darkMode ? "#80A7C9" : "#5A7FA2"
    readonly property color infoSoft: darkMode ? "#283745" : "#EDF3F8"

    readonly property color previewBackground: darkMode ? "#111216" : "#17181D"
    readonly property color timelineBackground: darkMode ? "#16181D" : "#1B1D23"
    readonly property color timelineSurface: darkMode ? "#1D2026" : "#23262D"
    readonly property color timelineRuler: darkMode ? "#262932" : "#2B2F37"
    readonly property color timelineText: "#C4C7D0"
    readonly property color clipVideo: "#6577A6"
    readonly property color clipAudio: "#5E8B77"
    readonly property color clipVoice: "#806FA3"
    readonly property color clipSubtitle: "#A07A55"
    readonly property color clipOverlay: "#568A92"

    readonly property color news: darkMode ? "#A08EA3" : "#786A7D"
    readonly property color story: darkMode ? "#AA91C3" : "#876AA0"
    readonly property color translate: darkMode ? "#77A89D" : "#56877C"
    readonly property color video: darkMode ? "#859BC1" : "#657CA5"
    readonly property color shorts: darkMode ? "#C59382" : "#A66E5B"
    readonly property color batch: darkMode ? "#B29B70" : "#8C754D"
}
