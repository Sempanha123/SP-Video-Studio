import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var styleData: controller ? controller.style : ({})

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm

        Text { text: "Style"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { text: "Preset"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        ComboBox {
            id: presetCombo
            Layout.fillWidth: true
            model: root.controller ? root.controller.presetList : []
            textRole: "name"
            onActivated: if (root.controller && currentIndex >= 0) root.controller.applyPreset(model[currentIndex].id)
        }
        Text { text: "Position"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        ComboBox {
            Layout.fillWidth: true
            model: ["Bottom", "Middle", "Top"]
            onActivated: if (root.controller) root.controller.setStyleValue("vertical_position", ["bottom","middle","top"][currentIndex])
        }
        Text { text: "Alignment"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        ComboBox {
            Layout.fillWidth: true
            model: ["Center", "Left", "Right"]
            onActivated: if (root.controller) root.controller.setStyleValue("alignment", ["center","left","right"][currentIndex])
        }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Font size"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Item { Layout.fillWidth: true }
            SpinBox {
                from: 18; to: 96; editable: true
                value: Math.round(root.styleData.font_size || 48)
                onValueModified: if (root.controller) root.controller.setStyleValue("font_size", value)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                text: "Background"
                checked: !!root.styleData.background_enabled
                onToggled: if (root.controller) root.controller.setStyleValue("background_enabled", checked)
            }
            CheckBox {
                text: "Shadow"
                checked: root.styleData.shadow_enabled === undefined ? true : !!root.styleData.shadow_enabled
                onToggled: if (root.controller) root.controller.setStyleValue("shadow_enabled", checked)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Max lines"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Item { Layout.fillWidth: true }
            SpinBox { from: 1; to: 4; value: root.styleData.max_lines || 2; onValueModified: if (root.controller) root.controller.setStyleValue("max_lines", value) }
        }
        SecondaryButton { Layout.fillWidth: true; text: "Save Style as Preset"; onClicked: savePresetDialog.open() }
    }

    Dialog {
        id: savePresetDialog
        modal: true
        title: "Save Subtitle Preset"
        standardButtons: Dialog.Save | Dialog.Cancel
        contentItem: TextField { id: presetName; placeholderText: "Preset name" }
        onAccepted: if (root.controller && presetName.text.trim().length > 0) root.controller.saveStylePreset(presetName.text.trim())
    }
}
