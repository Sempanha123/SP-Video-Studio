import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Rectangle {
    id: root
    property var source: ({})
    property bool selected: false
    signal selectedRequested(string id)
    signal refreshRequested(string id)
    signal removeRequested(string id)
    implicitHeight: 92; radius: Theme.radius.medium; color: selected ? Theme.colors.accentSoft : Theme.colors.surface2; border.color: selected ? Theme.colors.accent : Theme.colors.border
    MouseArea { anchors.fill: parent; onClicked: root.selectedRequested(root.source.id || "") }
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 4
        RowLayout { Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: root.source.title || root.source.url || "Untitled source"; elide: Text.ElideRight; color: Theme.colors.textPrimary; font.weight: Theme.type.semibold }
            StatusBadge { text: root.source.status || "pending"; status: root.source.status === "ready" ? "ready" : (root.source.status === "failed" ? "error" : "warning") }
        }
        Text { Layout.fillWidth: true; text: (root.source.publisher || root.source.type || "Source") + (root.source.publishedAt ? " · " + root.source.publishedAt : ""); color: Theme.colors.textMuted; elide: Text.ElideRight; font.pixelSize: Theme.type.caption }
        RowLayout { Layout.fillWidth: true; Text { text: (root.source.evidenceCount || 0) + " evidence link(s)"; color: Theme.colors.textSecondary; font.pixelSize: Theme.type.caption }; Item { Layout.fillWidth: true }; SecondaryButton { visible: root.source.type === "url"; text: "Refresh"; compact: true; onClicked: root.refreshRequested(root.source.id) }; IconButton { iconName: "trash"; tooltip: "Remove source"; onClicked: root.removeRequested(root.source.id) } }
    }
}
