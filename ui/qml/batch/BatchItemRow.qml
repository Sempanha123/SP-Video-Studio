import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Rectangle { id:root; property var itemData:({}); property var controller; signal selected(var data); height:50; color:mouse.containsMouse?Qt.rgba(1,1,1,0.035):"transparent"; border.color:Qt.rgba(1,1,1,0.07)
    MouseArea { id:mouse; anchors.fill:parent; hoverEnabled:true; onClicked:root.selected(root.itemData) }
    RowLayout { anchors.fill:parent; anchors.margins:8; spacing:10
        Text { text:(itemData.rowIndex+1); color:Theme.colors.textSecondary; Layout.preferredWidth:36 }
        Text { text:(itemData.resolvedData && (itemData.resolvedData.title || itemData.resolvedData.headline)) || itemData.itemKey || ""; color:Theme.colors.textPrimary; elide:Text.ElideRight; Layout.fillWidth:true }
        Text { text:(itemData.resolvedData && itemData.resolvedData.language) || "—"; color:Theme.colors.textSecondary; Layout.preferredWidth:52 }
        Text { text:(itemData.metadata && itemData.metadata.variant && itemData.metadata.variant.platform) || "—"; color:Theme.colors.textSecondary; Layout.preferredWidth:86 }
        Text { text:itemData.currentStage || ""; color:Theme.colors.textSecondary; Layout.preferredWidth:105 }
        ProgressBar { value:itemData.progress || 0; Layout.preferredWidth:88 }
        Text { text:Math.round((itemData.progress||0)*100)+"%"; color:Theme.colors.textSecondary; Layout.preferredWidth:42 }
        Text { text:itemData.status || ""; color:Theme.colors.textPrimary; Layout.preferredWidth:96 }
        ToolButton { text:"↻"; visible:itemData.status==="failed" || itemData.status==="interrupted" || itemData.status==="output_missing" || itemData.status==="needs_review"; onClicked:controller.retryItem(itemData.id) }
    }
}
