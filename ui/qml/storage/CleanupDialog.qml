import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    property var controller
    property bool clearAll: true
    property var selectedCategories: []
    property var chosenCategories: []
    property bool selectionChanged: false
    property string projectId: ""
    width: 520
    header: null; footer: null

    function rebuildChoices() {
        var rows = controller ? controller.cacheBreakdown : []
        var next = []
        for (var i = 0; i < rows.length; ++i)
            next.push(rows[i].category)
        chosenCategories = next
    }
    function setChosen(category, enabled) {
        var next = []
        for (var i = 0; i < chosenCategories.length; ++i)
            if (chosenCategories[i] !== category) next.push(chosenCategories[i])
        if (enabled) next.push(category)
        chosenCategories = next
        selectionChanged = true
        if (controller) controller.previewSelected(chosenCategories, projectId)
    }

    onOpened: {
        if (!controller) return
        selectionChanged = false
        if (clearAll) {
            rebuildChoices()
            controller.previewAllCache()
        } else {
            chosenCategories = selectedCategories.slice(0)
            controller.previewSelected(chosenCategories, projectId)
        }
    }

    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text { text: "Clear Cache"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: "The following temporary files can be recreated. Projects, source media, models, recovery copies and final exports are not part of this cleanup."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }

        ColumnLayout {
            visible: root.clearAll && root.controller && root.controller.cacheBreakdown.length > 0
            Layout.fillWidth: true
            spacing: Theme.spacing.xs
            Repeater {
                model: root.controller ? root.controller.cacheBreakdown : []
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    CheckBox {
                        checked: root.chosenCategories.indexOf(modelData.category) >= 0
                        onToggled: root.setChosen(modelData.category, checked)
                    }
                    Text { text: modelData.label || modelData.category; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; elide: Text.ElideRight }
                    Text { text: modelData.sizeDisplay || "0 B"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: 84
            RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md
                ColumnLayout { Layout.fillWidth: true; Text { text: "Temporary data"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }; Text { text: (controller ? controller.cleanupPreview.entryCount : 0) + " file(s)"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption } }
                Text { text: controller ? (controller.cleanupPreview.estimatedDisplay || "0 B") : "0 B"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
            }
        }
        Text { visible: controller && (controller.cleanupPreview.skippedActive || []).length > 0; text: (controller.cleanupPreview.skippedActive || []).length + " active file(s) will be skipped."; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Cancel"; onClicked: root.close() }
            AppButton {
                text: "Clear " + (controller ? (controller.cleanupPreview.estimatedDisplay || "Cache") : "Cache")
                enabled: controller && (controller.cleanupPreview.entryCount || 0) > 0
                onClicked: {
                    var ok = root.clearAll && !root.selectionChanged ? controller.clearAllCache() : controller.clearSelected(root.chosenCategories, root.projectId)
                    if (ok) root.close()
                }
            }
        }
    }
}
