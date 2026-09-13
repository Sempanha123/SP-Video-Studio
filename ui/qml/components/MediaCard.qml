import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id:root
    property string mediaId:""; property string mediaName:"Untitled media"; property string mediaType:"video"; property string typeName:"Video"; property string thumbnail:""; property string duration:""; property string resolution:""; property string fileSize:""; property string mediaStatus:"ready"; property string statusName:"Ready"; property bool isSelected:false
    signal activated(string mediaId); signal detailsRequested(string mediaId); signal revealRequested(string mediaId); signal removeRequested(string mediaId,string name)
    interactive:true; selected:isSelected; accessibleName:root.mediaName+". "+root.typeName+". "+root.secondaryLine()+". Status "+root.statusName; implicitHeight:Math.max(226,Math.round(226*Theme.textScale)); onClicked:root.activated(root.mediaId)
    Drag.active: dragHandler.active
    Drag.source: root
    Drag.keys: ["sp-video-studio-media", "sp-media-"+root.mediaType]
    Drag.hotSpot.x: width/2; Drag.hotSpot.y: 64
    function secondaryLine(){var values=[];if(root.resolution!=="")values.push(root.resolution);if(root.duration!=="")values.push(root.duration);if(values.length===0)values.push(root.typeName);return values.join(" · ")}
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.sm; spacing:Theme.spacing.sm
        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:128; radius:Theme.radius.medium; color:Theme.colors.surfaceHover; clip:true
            Image { anchors.fill:parent; source:root.thumbnail; visible:root.thumbnail!==""; fillMode:Image.PreserveAspectCrop; asynchronous:true; cache:true; smooth:true }
            Column { anchors.centerIn:parent; spacing:Theme.spacing.xs; visible:root.thumbnail===""
                Icon { anchors.horizontalCenter:parent.horizontalCenter; width:30;height:30;name:root.mediaType==="audio"?"audio":(root.mediaType==="image"?"image":"video") }
                Text { anchors.horizontalCenter:parent.horizontalCenter;text:root.mediaType==="audio"?"Audio":(root.mediaStatus==="missing"?"File Missing":root.typeName);color:root.mediaStatus==="missing"?Theme.colors.warning:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
            }
            StatusBadge { anchors.left:parent.left;anchors.top:parent.top;anchors.margins:Theme.spacing.sm;text:root.statusName;status:root.mediaStatus }
            IconButton { id:moreButton;anchors.right:parent.right;anchors.top:parent.top;anchors.margins:Theme.spacing.xs;iconName:"more";accessibleName:"Media actions for "+root.mediaName;tooltip:"Media actions";onClicked:actionsMenu.popup() }
            Rectangle { anchors.fill:parent; visible:dragHandler.active; color:"transparent"; border.color:Theme.colors.accent; border.width:2; radius:Theme.radius.medium }
        }
        ColumnLayout { Layout.fillWidth:true;spacing:2
            Text {
                id: mediaNameLabel
                Layout.fillWidth: true
                text: root.mediaName
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.body
                font.weight: Theme.type.semibold
                elide: Text.ElideMiddle
                ToolTip.visible: mediaNameHover.hovered && mediaNameLabel.truncated
                ToolTip.text: root.mediaName
                ToolTip.delay: Theme.tooltipDelay
                HoverHandler { id: mediaNameHover }
            }
            RowLayout { Layout.fillWidth:true;spacing:Theme.spacing.sm
                Text { Layout.fillWidth:true;text:root.secondaryLine();color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;elide:Text.ElideRight }
                Text { text:root.fileSize;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
            }
        }
    }
    DragHandler { id:dragHandler; target:null; acceptedButtons:Qt.LeftButton }
    TapHandler { acceptedButtons:Qt.RightButton;onTapped:actionsMenu.popup() }
    Menu { id:actionsMenu;width:188;background:Rectangle{radius:Theme.radius.medium;color:Theme.colors.surfaceRaised;border.color:Theme.colors.border;border.width:1}
        MenuItem { id:detailsAction;text:"View Details";contentItem:Text{text:detailsAction.text;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;verticalAlignment:Text.AlignVCenter};background:Rectangle{color:detailsAction.highlighted?Theme.colors.surfaceHover:"transparent";radius:Theme.radius.small};onTriggered:root.detailsRequested(root.mediaId) }
        MenuItem { id:revealAction;text:"Reveal in Folder";contentItem:Text{text:revealAction.text;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;verticalAlignment:Text.AlignVCenter};background:Rectangle{color:revealAction.highlighted?Theme.colors.surfaceHover:"transparent";radius:Theme.radius.small};onTriggered:root.revealRequested(root.mediaId) }
        MenuSeparator { contentItem:Rectangle{implicitHeight:1;color:Theme.colors.border} }
        MenuItem { id:removeAction;text:root.mediaStatus==="missing"?"Remove Reference":"Remove from Project";contentItem:Text{text:removeAction.text;color:Theme.colors.danger;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;verticalAlignment:Text.AlignVCenter};background:Rectangle{color:removeAction.highlighted?Theme.colors.dangerSoft:"transparent";radius:Theme.radius.small};onTriggered:root.removeRequested(root.mediaId,root.mediaName) }
    }
}
