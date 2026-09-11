import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var templateData: ({})
    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 170; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; clip: true
            Image { anchors.fill: parent; source: templateData.previewImage || ""; visible: source !== ""; fillMode: Image.PreserveAspectCrop; asynchronous: true }
            Column { anchors.centerIn: parent; visible: templateData.previewImage === undefined || templateData.previewImage === ""; spacing: 8
                Icon { anchors.horizontalCenter: parent.horizontalCenter; width: 42; height: 42; name: "template" }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Static template preview"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
        }
        Text { text: templateData.name || "Choose a template"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: templateData.description || "Select a template to see its structure, placeholders and compatibility."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        GridLayout { Layout.fillWidth: true; columns: 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.xs
            Text { text: "Workflow"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: templateData.workflow || "—"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Text { text: "Aspects"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: (templateData.aspects || []).join(", ") || "Project default"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            Text { text: "Features"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { Layout.fillWidth: true; text: (templateData.features || []).join(", ") || "Core editor"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
        }
        Text { text: "Required setup"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
        Repeater { model: templateData.requiredPlaceholders || []; delegate: Text { required property var modelData; Layout.fillWidth: true; text: "• " + (modelData.label || modelData.id); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; wrapMode: Text.WordWrap } }
        Item { Layout.fillHeight: true }
    }
}
