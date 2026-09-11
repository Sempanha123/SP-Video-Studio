import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var templateData: ({})
    signal selected(string templateId)
    signal useRequested(string templateId)
    implicitHeight: 198
    interactive: true
    onClicked: root.selected(templateData.id || "")

    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            Rectangle { width: 38; height: 38; radius: Theme.radius.medium; color: Theme.colors.accentSoft
                Icon { anchors.centerIn: parent; width: 20; height: 20; name: (templateData.workflow === "news" ? "news" : templateData.workflow === "story" ? "story" : templateData.workflow === "shorts" ? "shorts" : "template") }
            }
            ColumnLayout { Layout.fillWidth: true; spacing: 1
                Text { Layout.fillWidth: true; text: templateData.name || "Template"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                Text { text: (templateData.category || "General") + " · " + (templateData.builtin ? "Built-in" : "User"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            StatusBadge { text: templateData.version ? "v" + templateData.version : "v1.0"; status: "neutral" }
        }
        Text { Layout.fillWidth: true; Layout.preferredHeight: 42; text: templateData.description || "Reusable project structure and style."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; elide: Text.ElideRight; maximumLineCount: 2 }
        Flow {
            Layout.fillWidth: true; spacing: 5
            Repeater { model: (templateData.aspects || []).slice(0,3); delegate: StatusBadge { required property var modelData; text: String(modelData); status: "neutral" } }
            Repeater { model: (templateData.features || []).slice(0,3); delegate: StatusBadge { required property var modelData; text: String(modelData).replaceAll("_"," "); status: "info" } }
        }
        Item { Layout.fillHeight: true }
        RowLayout { Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: (templateData.requiredPlaceholders || []).length + " required setup item(s)"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppButton { text: "Use"; compact: true; onClicked: root.useRequested(templateData.id || "") }
        }
    }
}
