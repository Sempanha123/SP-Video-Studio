import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Button {
    id: root
    property string iconName: ""
    property bool selected: false
    implicitHeight: 38
    leftPadding: Theme.spacing.sm; rightPadding: Theme.spacing.sm
    contentItem: RowLayout {
        spacing: Theme.spacing.md
        Rectangle { visible: root.selected; Layout.preferredWidth: 3; Layout.preferredHeight: 18; radius: 2; color: Theme.colors.accent }
        Icon { name: root.iconName; Layout.preferredWidth: 17; Layout.preferredHeight: 17; opacity: root.selected ? 1 : 0.72 }
        Text { Layout.fillWidth: true; text: root.text; color: root.selected ? Theme.colors.accent : Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: root.selected ? Theme.type.semibold : Theme.type.medium; elide: Text.ElideRight }
    }
    background: Rectangle { radius: Theme.radius.small; color: root.selected ? Theme.colors.accentSoft : (root.hovered ? Theme.colors.surfaceHover : "transparent"); Behavior on color { ColorAnimation { duration: Theme.animation.fast } } }
}
