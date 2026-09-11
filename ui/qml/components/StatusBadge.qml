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
        if (status === "installed" || status === "ready" || status === "completed") return Theme.colors.successSoft
        if (status === "failed") return Theme.colors.dangerSoft
        if (status === "running") return Theme.colors.infoSoft
        if (status === "offline" || status === "not-installed") return Theme.colors.warningSoft
        return Theme.colors.surfaceHover
    }
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: {
            if (root.status === "installed" || root.status === "ready" || root.status === "completed") return Theme.colors.success
            if (root.status === "failed") return Theme.colors.danger
            if (root.status === "running") return Theme.colors.info
            if (root.status === "offline" || root.status === "not-installed") return Theme.colors.warning
            return Theme.colors.textSecondary
        }
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
        font.weight: Theme.type.semibold
    }
}
