import QtQuick 2.15
import "../theme"

Rectangle {
    id: root
    property string text: "Ready"
    property string status: "ready"
    implicitWidth: label.implicitWidth + Theme.spacing.md * 2
    implicitHeight: 24
    radius: 12
    color: {
        if (["installed", "ready", "completed"].indexOf(status) >= 0) return Theme.colors.successSoft
        if (["failed", "critical", "setup-required"].indexOf(status) >= 0) return Theme.colors.dangerSoft
        if (["running", "checking"].indexOf(status) >= 0) return Theme.colors.infoSoft
        if (["offline", "not-installed", "warning", "ready-with-warnings", "possibly_available"].indexOf(status) >= 0) return Theme.colors.warningSoft
        return Theme.colors.surfaceHover
    }
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: {
            if (["installed", "ready", "completed"].indexOf(root.status) >= 0) return Theme.colors.success
            if (["failed", "critical", "setup-required"].indexOf(root.status) >= 0) return Theme.colors.danger
            if (["running", "checking"].indexOf(root.status) >= 0) return Theme.colors.info
            if (["offline", "not-installed", "warning", "ready-with-warnings", "possibly_available"].indexOf(root.status) >= 0) return Theme.colors.warning
            return Theme.colors.textSecondary
        }
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
        font.weight: Theme.type.semibold
    }
}
