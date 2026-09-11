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
        if (["failed", "invalid", "critical", "setup-required", "repair_required", "repair-required", "not_recommended"].indexOf(status) >= 0) return Theme.colors.dangerSoft
        if (["running", "processing", "checking", "downloading", "verifying", "installing"].indexOf(status) >= 0) return Theme.colors.infoSoft
        if (["offline", "missing", "not-installed", "not_installed", "paused", "warning", "ready-with-warnings", "possibly_available", "compatible_with_warning"].indexOf(status) >= 0) return Theme.colors.warningSoft
        return Theme.colors.surfaceHover
    }
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: {
            if (["installed", "ready", "completed"].indexOf(root.status) >= 0) return Theme.colors.success
            if (["failed", "invalid", "critical", "setup-required", "repair_required", "repair-required", "not_recommended"].indexOf(root.status) >= 0) return Theme.colors.danger
            if (["running", "processing", "checking", "downloading", "verifying", "installing"].indexOf(root.status) >= 0) return Theme.colors.info
            if (["offline", "missing", "not-installed", "not_installed", "paused", "warning", "ready-with-warnings", "possibly_available", "compatible_with_warning"].indexOf(root.status) >= 0) return Theme.colors.warning
            return Theme.colors.textSecondary
        }
        font.family: Theme.type.family
        font.pixelSize: Theme.type.caption
        font.weight: Theme.type.semibold
    }
}
