import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../theme"

RowLayout {
    id: root
    property var controller
    spacing: Theme.spacing.xs

    IconButton {
        iconName: root.controller && root.controller.muted ? "mute" : "volume"
        tooltip: root.controller && root.controller.muted ? "Unmute (M)" : "Mute (M)"
        enabled: root.controller !== null
        onClicked: if (root.controller) root.controller.toggleMute()
    }

    Slider {
        id: volumeSlider
        Layout.preferredWidth: 84
        from: 0
        to: 100
        value: root.controller ? root.controller.volume : 100
        enabled: root.controller !== null
        onMoved: if (root.controller) root.controller.setVolume(Math.round(value))
        ToolTip.visible: hovered
        ToolTip.text: Math.round(value) + "%"

        Connections {
            target: root.controller
            ignoreUnknownSignals: true
            function onVolumeChanged() {
                if (!volumeSlider.pressed && root.controller)
                    volumeSlider.value = root.controller.volume
            }
        }
    }
}
