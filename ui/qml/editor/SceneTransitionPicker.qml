import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property var controller
    property var scene: ({})
    spacing: Theme.spacing.sm

    Text { text: "Transition"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
    ComboBox {
        id: typeBox
        Layout.fillWidth: true
        model: ["Cut", "Fade", "Crossfade", "Slide"]
        Component.onCompleted: sync()
        function sync() {
            var value = root.scene.transitionOut ? root.scene.transitionOut.type : "cut"
            currentIndex = Math.max(0, ["cut","fade","crossfade","slide"].indexOf(value))
        }
        onActivated: durationBox.enabled = currentIndex !== 0
    }
    RowLayout {
        Layout.fillWidth: true
        Text { text: "Duration"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        SpinBox { id: durationBox; from: 0; to: 3000; stepSize: 100; value: root.scene.transitionOut ? (root.scene.transitionOut.durationMs || 0) : 0; editable: true; enabled: typeBox.currentIndex !== 0; Layout.fillWidth: true }
        Text { text: "ms"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
    SecondaryButton {
        text: "Apply Transition"; compact: true
        onClicked: if (root.controller) root.controller.setTransition(["cut","fade","crossfade","slide"][typeBox.currentIndex], typeBox.currentIndex === 0 ? 0 : durationBox.value)
    }
}
