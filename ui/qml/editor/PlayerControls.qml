import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"

Rectangle {
    id: root
    property var controller
    property bool playable: controller && (controller.selectedType === "video" || controller.selectedType === "audio")
    implicitHeight: playable ? 64 : 0
    visible: playable
    color: Theme.colors.surface
    border.color: Theme.colors.border
    border.width: 1
    radius: Theme.radius.medium

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.md
        anchors.rightMargin: Theme.spacing.md
        spacing: Theme.spacing.sm

        IconButton {
            iconName: root.controller && root.controller.state === "playing" ? "pause" : (root.controller && root.controller.state === "ended" ? "replay" : "play")
            tooltip: root.controller && root.controller.state === "playing" ? "Pause (Space)" : (root.controller && root.controller.state === "ended" ? "Replay (Space)" : "Play (Space)")
            enabled: root.controller && root.controller.state !== "loading" && root.controller.state !== "error"
            onClicked: if (root.controller) root.controller.togglePlayback()
        }

        Text {
            text: root.controller ? root.controller.positionText : "00:00"
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: 48
        }

        SeekBar {
            Layout.fillWidth: true
            Layout.minimumWidth: 120
            controller: root.controller
        }

        Text {
            text: root.controller ? root.controller.durationText : "00:00"
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            Layout.preferredWidth: 48
        }

        VolumeControl { controller: root.controller }
    }
}
