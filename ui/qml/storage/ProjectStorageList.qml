import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property var controller
    property var projects: controller ? controller.projects : []
    signal openProjectRequested(string projectId)
    spacing: Theme.spacing.sm

    SectionHeader { Layout.fillWidth: true; title: "Projects"; description: "Largest projects first. Clearing cache does not remove scripts, source media, subtitles, project databases, or final exports." }
    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(360, Math.max(80, contentHeight))
        model: root.projects
        spacing: Theme.spacing.sm
        clip: true
        reuseItems: true
        cacheBuffer: 400
        delegate: AppCard {
            required property var modelData
            width: ListView.view.width
            implicitHeight: 78
            RowLayout {
                anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.md
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 2
                    Text { text: modelData.name || "Project"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight; Layout.fillWidth: true }
                    Text { text: (modelData.mediaDisplay || "0 B") + " media · " + (modelData.cacheDisplay || "0 B") + " cache · " + (modelData.exportsDisplay || "0 B") + " renders/exports"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; elide: Text.ElideRight; Layout.fillWidth: true }
                }
                Text { text: modelData.totalDisplay || "0 B"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                SecondaryButton { text: "Open Folder"; compact: true; onClicked: root.controller.openFolder(modelData.root) }
                SecondaryButton { text: "Clear Cache"; compact: true; onClicked: root.controller.clearProjectCache(modelData.projectId) }
            }
        }
    }
}
