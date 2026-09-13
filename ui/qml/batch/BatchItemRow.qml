import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Rectangle {
    id: root; property var itemData: ({}); property var controller; signal selected(var data)
    property string itemName:(itemData.resolvedData && (itemData.resolvedData.title || itemData.resolvedData.headline)) || itemData.itemKey || "Batch item"
    height:Math.max(48, Math.round(48*Theme.textScale));radius:Theme.radius.small;color:mouse.containsMouse?Theme.colors.surfaceHover:"transparent";border.width:1;border.color:activeFocus?Theme.colors.focus:Theme.colors.border
    activeFocusOnTab:true
    Accessible.role:Accessible.ListItem
    Accessible.name:itemName+". Language "+((itemData.resolvedData&&itemData.resolvedData.language)||"not set")+". Stage "+(itemData.currentStage||"pending")+". "+Math.round(Number(itemData.progress||0)*100)+" percent. Status "+String(itemData.status||"pending").replaceAll("_"," ")
    MouseArea{id:mouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:{root.forceActiveFocus(Qt.MouseFocusReason);root.selected(root.itemData)}}
    Keys.onReturnPressed:function(event){root.selected(root.itemData);event.accepted=true}
    Keys.onSpacePressed:function(event){root.selected(root.itemData);event.accepted=true}
    RowLayout { anchors.fill:parent;anchors.leftMargin:10;anchors.rightMargin:8;spacing:Theme.spacing.sm
        Text{text:(itemData.rowIndex+1);color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;Layout.preferredWidth:30}
        Text{id:titleLabel;text:root.itemName;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;elide:Text.ElideRight;Layout.fillWidth:true;ToolTip.visible:titleHover.hovered&&titleLabel.truncated;ToolTip.text:text;ToolTip.delay:Theme.tooltipDelay;HoverHandler{id:titleHover}}
        Text{text:(itemData.resolvedData&&itemData.resolvedData.language)||"—";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;Layout.preferredWidth:48}
        Text{text:itemData.currentStage||"";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;Layout.preferredWidth:96;elide:Text.ElideRight}
        SoftProgressBar{value:itemData.progress||0;accessibleName:"Batch item progress";Layout.preferredWidth:78}
        StatusBadge{text:String(itemData.status||"pending").replaceAll("_"," ");status:String(itemData.status||"pending")}
        ToolButton{text:"↻";visible:itemData.status==="failed"||itemData.status==="interrupted"||itemData.status==="output_missing"||itemData.status==="needs_review";Accessible.name:"Retry batch item";Accessible.role:Accessible.Button;ToolTip.visible:hovered;ToolTip.text:"Retry item";ToolTip.delay:Theme.tooltipDelay;onClicked:controller.retryItem(itemData.id);background:Rectangle{radius:Theme.radius.small;color:parent.hovered?Theme.colors.surfaceHover:"transparent"}}
    }
}
