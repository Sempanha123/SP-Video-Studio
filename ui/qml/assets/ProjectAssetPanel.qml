import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase25 1.0
import "../theme"
import "../components"
ColumnLayout {
    id:root
    property string workflow:"video"
    spacing:Theme.spacing.xs
    RowLayout { Layout.fillWidth:true
        AppTextField { Layout.fillWidth:true; placeholderText:"Search reusable assets"; onTextChanged:AssetLibrary.setQuery(text) }
        AppComboBox {
            id:filter
            model: root.workflow==="news" ? ["All","B-roll","Reporter","Presenter","Background","Logo"] : (root.workflow==="story" ? ["All","Character","B-roll","Background","Music"] : (root.workflow==="shorts" ? ["All","B-roll","Presenter","Music","SFX","Overlay"] : ["All","Video","Image","Audio","B-roll","Presenter","Music","SFX"]))
            onCurrentTextChanged:AssetLibrary.setFilter(currentText.toLowerCase().replaceAll(" ","-").replace("b-roll","broll"))
        }
    }
    ListView {
        Layout.fillWidth:true;Layout.fillHeight:true;clip:true;reuseItems:true;spacing:4;model:AssetLibrary.assets
        delegate:Rectangle {
            required property var modelData
            width:ListView.view.width;height:54;radius:Theme.radius.medium;color:Theme.colors.surfaceHover
            property string assetId:modelData.id||"";property string mediaType:modelData.type||""
            Drag.active:drag.active;Drag.source:this;Drag.keys:["sp-global-asset","sp-global-asset-"+mediaType];Drag.supportedActions:Qt.CopyAction
            DragHandler{id:drag;target:null}
            RowLayout { anchors.fill:parent;anchors.margins:7
                Icon { width:18;height:18;name:mediaType==="audio"?"mic":(mediaType==="image"?"image":"video") }
                ColumnLayout { Layout.fillWidth:true;spacing:0
                    Text { Layout.fillWidth:true;text:modelData.name||"Asset";elide:Text.ElideRight;color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall }
                    Text { text:(modelData.subtype||mediaType).replaceAll("_"," ");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:10 }
                }
                SecondaryButton { text:"Add";compact:true;onClicked:AssetLibrary.addToCurrentProject(modelData.id) }
            }
        }
    }
    Text { visible:AssetLibrary.assets.length===0;text:"No matching reusable assets.";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
}
