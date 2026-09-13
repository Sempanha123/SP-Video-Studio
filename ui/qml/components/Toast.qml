import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle {
    id: root
    property string message: ""
    property string technicalMessage: ""
    property string variant: "info"
    property int timeout: 3000
    width: Math.min(420, toastText.implicitWidth + Theme.spacing.xxl * 2)
    height: Math.max(44, toastText.implicitHeight + Theme.spacing.lg * 2)
    radius: Theme.radius.medium
    color: Theme.colors.surfaceRaised
    border.color: variant === "error" ? Theme.colors.danger : (variant === "warning" ? Theme.colors.warning : (variant === "success" ? Theme.colors.success : Theme.colors.borderStrong))
    border.width: 1; opacity: 0; visible: opacity > 0; z: 1000
    Accessible.name: message
    Accessible.role: Accessible.AlertMessage
    function friendlyMessage(text) {
        var raw = String(text || "").trim()
        if (raw.indexOf("Traceback") >= 0 || raw.indexOf("sqlite3.") >= 0 || raw.indexOf("FFmpeg filter") >= 0 || raw.indexOf("filter_complex") >= 0)
            return "The operation could not be completed. Check the related media, model or settings and try again."
        return raw || "The operation could not be completed."
    }
    function show(text, kind, duration) { technicalMessage = String(text || ""); message = friendlyMessage(text); variant = kind || "info"; timeout = duration || 3000; opacity = 1; timer.restart() }
    Text { id: toastText; anchors.fill: parent; anchors.margins: Theme.spacing.lg; text: root.message; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; verticalAlignment: Text.AlignVCenter; lineHeightMode: Text.ProportionalHeight; lineHeight: Theme.type.normalLineHeight }
    Timer { id: timer; interval: root.timeout; onTriggered: root.opacity = 0 }
    Behavior on opacity { NumberAnimation { duration: Theme.animation.normal } }
}
