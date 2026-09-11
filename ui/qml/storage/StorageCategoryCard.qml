import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property string title: "Cache"
    property string sizeText: "0 B"
    property string description: ""
    property string safety: "safe_to_clear"
    property bool manageable: true
    signal manageRequested()
    implicitHeight: 138

    function safetyLabel() {
        if (safety === "safe_to_clear") return "Safe to Clear"
        if (safety === "regeneratable") return "Regeneratable"
        if (safety === "protected") return "Protected"
        if (safety === "external") return "External"
        return "User Files"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            Text { text: root.title; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold; elide: Text.ElideRight }
            StatusBadge { text: root.safetyLabel(); status: root.safety === "safe_to_clear" || root.safety === "regeneratable" ? "ready" : (root.safety === "protected" ? "warning" : "unknown") }
        }
        Text { text: root.sizeText; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
        Text { Layout.fillWidth: true; text: root.description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
        Item { Layout.fillHeight: true }
        SecondaryButton { visible: root.manageable; text: "Manage"; compact: true; onClicked: root.manageRequested() }
    }
}
