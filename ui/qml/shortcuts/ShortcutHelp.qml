import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

Popup {
    id:root;modal:true;focus:true;width:Math.min(700,parent?parent.width-48:700);height:Math.min(620,parent?parent.height-64:620);x:parent?(parent.width-width)/2:0;y:parent?(parent.height-height)/2:0;padding:0;closePolicy:Popup.CloseOnEscape|Popup.CloseOnPressOutside
    background:Rectangle{radius:Theme.radius.large;color:Theme.colors.surfaceRaised;border.color:Theme.colors.borderStrong}
    property var rows:[]
    function refresh(){rows=Shortcuts.search(search.text)}
    onOpened:{Commands.setModalOpen(true);rows=Shortcuts.rows;search.forceActiveFocus()}
    onClosed:{Commands.setModalOpen(false);Commands.setTextEditing(false)}
    contentItem:ColumnLayout{anchors.fill:parent;anchors.margins:Theme.spacing.lg;spacing:Theme.spacing.md
        RowLayout{Layout.fillWidth:true;Text{Layout.fillWidth:true;text:"Keyboard Shortcuts";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.titleLarge;font.weight:Theme.type.semibold}SecondaryButton{text:"Close";onClicked:root.close()}}
        AppTextField{id:search;Layout.fillWidth:true;placeholderText:"Search General, Playback, Timeline, Speech…";onTextChanged:root.refresh()}
        ListView{Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:root.rows;section.property:"category";section.criteria:ViewSection.FullString;section.delegate:Rectangle{width:ListView.view.width;height:34;color:Theme.colors.surfaceAlt;Text{anchors.left:parent.left;anchors.leftMargin:Theme.spacing.sm;anchors.verticalCenter:parent.verticalCenter;text:section;color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;font.weight:Theme.type.semibold}}
            delegate:RowLayout{required property var modelData;width:ListView.view.width;height:40;Text{Layout.fillWidth:true;text:modelData.name;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.body}Text{text:modelData.shortcut||"—";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodyStrong}}
            ScrollBar.vertical:ScrollBar{}
        }
    }
}
