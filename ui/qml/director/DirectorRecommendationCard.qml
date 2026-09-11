import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var recommendation
    property var controller
    implicitHeight: content.implicitHeight + Theme.spacing.lg * 2
    ColumnLayout {
        id: content; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: (root.recommendation.title || root.recommendation.category || "Recommendation").toUpperCase(); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
            AppButton { text: root.recommendation.locked ? "Locked" : "Lock"; compact: true; variant: root.recommendation.locked ? "secondary" : "ghost"; onClicked: root.controller.lockRecommendation(root.recommendation.category, !root.recommendation.locked) }
        }
        Text { Layout.fillWidth: true; text: typeof root.recommendation.value === "object" ? JSON.stringify(root.recommendation.value) : String(root.recommendation.value); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; wrapMode: Text.WordWrap }
        Text { Layout.fillWidth: true; text: root.recommendation.reason || ""; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        RowLayout {
            Layout.fillWidth: true
            StatusBadge { visible: root.recommendation.userModified; text: "Edited"; status: "warning" }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Regenerate"; compact: true; enabled: !root.recommendation.locked; onClicked: root.controller.regenerate(root.recommendation.category) }
            SecondaryButton { text: "Change"; compact: true; onClicked: editDialog.open() }
        }
    }
    Dialog {
        id: editDialog; modal: true; width: 420; title: "Change recommendation"; standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { text: root.recommendation.title || "Recommendation"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
            AppTextField { id: valueField; Layout.fillWidth: true; text: typeof root.recommendation.value === "object" ? JSON.stringify(root.recommendation.value) : String(root.recommendation.value) }
        }
        onOpened: valueField.text = typeof root.recommendation.value === "object" ? JSON.stringify(root.recommendation.value) : String(root.recommendation.value)
        onAccepted: {
            var value = valueField.text
            if (root.recommendation.category === "scenes") value = parseInt(valueField.text)
            else if (valueField.text.length > 1 && (valueField.text[0] === "{" || valueField.text[0] === "[")) {
                try { value = JSON.parse(valueField.text) } catch (e) { value = valueField.text }
            }
            root.controller.editRecommendation(root.recommendation.category, value)
        }
    }
}
