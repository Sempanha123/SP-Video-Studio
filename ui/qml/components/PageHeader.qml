import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item {
    id: root
    property string title: ""
    property string description: ""
    property alias actions: actionHost.data
    implicitHeight: description.length ? 58 : 40
    RowLayout {
        anchors.fill: parent; spacing: Theme.spacing.lg
        ColumnLayout {
            Layout.fillWidth: true; spacing: 2
            Text { Layout.fillWidth: true; text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.pageTitle; font.weight: Theme.type.semibold; elide: Text.ElideRight }
            Text { visible: root.description.length > 0; Layout.fillWidth: true; text: root.description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.small; wrapMode: Text.WordWrap; maximumLineCount: 2 }
        }
        RowLayout { id: actionHost; spacing: Theme.spacing.sm }
    }
}
