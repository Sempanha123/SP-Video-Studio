import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property string title: ""
    property string description: ""
    default property alias content: body.data
    spacing: Theme.spacing.lg
    Accessible.name: title

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.spacing.xs
        Text { Layout.fillWidth: true; text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold; wrapMode: Text.WordWrap }
        Text { Layout.fillWidth: true; text: root.description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; lineHeight: 1.25 }
    }
    ColumnLayout { id: body; Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.spacing.md }
}
