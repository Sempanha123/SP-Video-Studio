import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { property var itemData:({}); property var controller
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.sm
        Text { text:"Item Details"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
        Text { text:itemData.itemKey || "Select an item"; color:Theme.colors.textPrimary; wrapMode:Text.WordWrap; Layout.fillWidth:true }
        Text { text:"Stage: "+(itemData.currentStage||"—"); color:Theme.colors.textSecondary }
        Text { text:"Output: "+(itemData.outputPath||"—"); color:Theme.colors.textSecondary; wrapMode:Text.WrapAnywhere; Layout.fillWidth:true }
        Button { text:"Open Generated Project"; enabled:!!itemData.projectId; onClicked:controller.openGeneratedProject(itemData.id) }
        TextArea { Layout.fillWidth:true; Layout.fillHeight:true; readOnly:true; text:JSON.stringify(itemData.resolvedData || {},null,2); wrapMode:TextArea.Wrap }
    }
}
