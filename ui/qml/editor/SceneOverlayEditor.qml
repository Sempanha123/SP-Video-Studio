import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property var controller
    property var overlays: []
    signal addLogoRequested()
    spacing: Theme.spacing.sm

    RowLayout {
        Layout.fillWidth: true
        Text { text: "Text & Overlays"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
        Item { Layout.fillWidth: true }
        AppButton { text: "Headline"; compact: true; variant: "ghost"; onClicked: if (root.controller) root.controller.addHeadline("Headline") }
        AppButton { text: "Lower Third"; compact: true; variant: "ghost"; onClicked: if (root.controller) root.controller.addLowerThird("Name", "Role") }
        AppButton { text: "Logo"; compact: true; variant: "ghost"; onClicked: root.addLogoRequested() }
    }

    Repeater {
        model: root.overlays || []
        delegate: AppCard {
            Layout.fillWidth: true
            implicitHeight: modelData.type === "logo" ? 110 : 178
            ColumnLayout {
                anchors.fill: parent; anchors.margins: Theme.spacing.sm; spacing: Theme.spacing.xs
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: (modelData.type || "overlay").replace("_", " ").toUpperCase(); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
                    Item { Layout.fillWidth: true }
                    IconButton { iconName: "up"; tooltip: "Bring forward"; onClicked: if (root.controller) root.controller.moveOverlay(modelData.id, 1) }
                    IconButton { iconName: "down"; tooltip: "Send backward"; onClicked: if (root.controller) root.controller.moveOverlay(modelData.id, -1) }
                    IconButton { iconName: "trash"; tooltip: "Delete overlay"; onClicked: if (root.controller) root.controller.deleteOverlay(modelData.id) }
                }
                TextField {
                    id: primaryField
                    visible: modelData.type !== "logo"
                    Layout.fillWidth: true
                    text: modelData.text || ""
                    placeholderText: "Overlay text"
                    onEditingFinished: if (root.controller) root.controller.updateOverlayText(modelData.id, text, secondaryField.text)
                }
                TextField {
                    id: secondaryField
                    visible: modelData.type === "lower_third"
                    Layout.fillWidth: true
                    text: modelData.secondaryText || ""
                    placeholderText: "Secondary text"
                    onEditingFinished: if (root.controller) root.controller.updateOverlayText(modelData.id, primaryField.text, text)
                }
                Text { visible: modelData.type === "logo"; text: modelData.assetName || "Logo image"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                GridLayout {
                    Layout.fillWidth: true; columns: 6; columnSpacing: Theme.spacing.xs; rowSpacing: Theme.spacing.xs
                    Text { text: "X"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: xBox; from: 0; to: 100; value: Math.round((modelData.x || 0) * 100); editable: true }
                    Text { text: "Y"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: yBox; from: 0; to: 100; value: Math.round((modelData.y || 0) * 100); editable: true }
                    Text { text: "Opacity"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: opacityBox; from: 0; to: 100; value: Math.round((modelData.opacity === undefined ? 1 : modelData.opacity) * 100); editable: true }
                    Text { text: "W"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: wBox; from: 1; to: 100; value: Math.round((modelData.width || .2) * 100); editable: true }
                    Text { text: "H"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: hBox; from: 1; to: 100; value: Math.round((modelData.height || .1) * 100); editable: true }
                    SecondaryButton {
                        text: "Apply Layout"; compact: true
                        onClicked: if (root.controller) root.controller.updateOverlayLayout(modelData.id, xBox.value/100, yBox.value/100, wBox.value/100, hBox.value/100, opacityBox.value/100)
                    }
                }
            }
        }
    }
}
