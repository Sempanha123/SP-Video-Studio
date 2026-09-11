import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string templateName: "Modern News"
    property string description: "Clean editorial layout"
    property string iconName: "template"
    implicitHeight: 118
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        Rectangle { width: 34; height: 34; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; Icon { anchors.centerIn: parent; width: 18; height: 18; name: root.iconName } }
        Text { text: root.templateName; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { text: root.description; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
}
