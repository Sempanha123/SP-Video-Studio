import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Rectangle {
    id: root; property var itemData: ({}); property var controller; signal selected(var data)
    height: 48; radius: Theme.radius.small; color: mouse.containsMouse ? Theme.colors.surfaceHover : "transparent"; border.width: 1; border.color: Theme.colors.border
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.selected(root.itemData) }
    RowLayout { anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 8; spacing: Theme.spacing.sm
        Text { text: (itemData.rowIndex+1); color: Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; Layout.preferredWidth: 30 }
        Text { text: (itemData.resolvedData && (itemData.resolvedData.title || itemData.resolvedData.headline)) || itemData.itemKey || ""; color: Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall; elide: Text.ElideRight; Layout.fillWidth: true }
        Text { text: (itemData.resolvedData && itemData.resolvedData.language) || "—"; color: Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; Layout.preferredWidth: 48 }
        Text { text: itemData.currentStage || ""; color: Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption; Layout.preferredWidth: 96; elide:Text.ElideRight }
        SoftProgressBar { value: itemData.progress || 0; Layout.preferredWidth: 78 }
        StatusBadge { text: String(itemData.status || "pending").replaceAll("_"," "); status: String(itemData.status || "pending") }
        ToolButton { text: "↻"; visible: itemData.status === "failed" || itemData.status === "interrupted" || itemData.status === "output_missing" || itemData.status === "needs_review"; ToolTip.visible:hovered; ToolTip.text:"Retry item"; onClicked: controller.retryItem(itemData.id); background:Rectangle{radius:Theme.radius.small;color:parent.hovered?Theme.colors.surfaceHover:"transparent"} }
    }
}
