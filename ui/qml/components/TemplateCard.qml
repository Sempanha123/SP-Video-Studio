import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string templateName: "Modern News"
    property string description: "Clean editorial layout"
    property string iconName: "template"
    accessibleName: root.templateName + ". " + root.description
    implicitHeight: Math.max(118, Math.round(118 * Theme.textScale))
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        Rectangle { width: 34; height: 34; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; Icon { anchors.centerIn: parent; width: 18; height: 18; name: root.iconName } }
        Text {
            id: templateNameLabel
            Layout.fillWidth: true
            text: root.templateName
            elide: Text.ElideRight
            color: Theme.colors.textPrimary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.heading
            font.weight: Theme.type.semibold
            ToolTip.visible: templateNameHover.hovered && templateNameLabel.truncated
            ToolTip.text: root.templateName
            ToolTip.delay: Theme.tooltipDelay
            HoverHandler { id: templateNameHover }
        }
        Text { Layout.fillWidth:true; text: root.description; wrapMode:Text.WordWrap; maximumLineCount:2; elide:Text.ElideRight; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
}
