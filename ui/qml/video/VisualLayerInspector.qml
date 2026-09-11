import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

ColumnLayout {
    id: root
    property var layer: VideoStudio.selectedLayer
    spacing: Theme.spacing.sm
    visible: !!layer.id
    Text { text:"Visual Layer"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.headingSmall; font.weight:Theme.type.semibold }
    Text { text:(layer.role||"Layer").replaceAll("_"," ")+" · Z "+Number(layer.zOrder||0); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
    GridLayout { Layout.fillWidth:true; columns:4; columnSpacing:6; rowSpacing:4
        Text { text:"X"; color:Theme.colors.textMuted } AppTextField { id:xField; text:Number(layer.x||0).toFixed(3) }
        Text { text:"Y"; color:Theme.colors.textMuted } AppTextField { id:yField; text:Number(layer.y||0).toFixed(3) }
        Text { text:"W"; color:Theme.colors.textMuted } AppTextField { id:wField; text:Number(layer.width||1).toFixed(3) }
        Text { text:"H"; color:Theme.colors.textMuted } AppTextField { id:hField; text:Number(layer.height||1).toFixed(3) }
        Text { text:"Opacity"; color:Theme.colors.textMuted } AppTextField { id:oField; text:Number(layer.opacity===undefined?1:layer.opacity).toFixed(2) }
        Text { text:"Rotate"; color:Theme.colors.textMuted } AppTextField { id:rField; text:Number(layer.rotation||0).toFixed(1) }
    }
    AppButton { text:"Apply Transform"; compact:true; onClicked:VideoStudio.setLayerTransform(layer.id,Number(xField.text),Number(yField.text),Number(wField.text),Number(hField.text),Number(oField.text),Number(rField.text)) }
    Text { text:"Picture in Picture"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
    Flow { Layout.fillWidth:true; spacing:4
        Repeater { model:[{n:"Top L",v:"top_left"},{n:"Top R",v:"top_right"},{n:"Bottom L",v:"bottom_left"},{n:"Bottom R",v:"bottom_right"},{n:"Center",v:"center"}]
            delegate:SecondaryButton { required property var modelData; text:modelData.n; compact:true; onClicked:VideoStudio.applyPip(root.layer.id,modelData.v) }
        }
    }
    Text { text:"Green / Blue Screen"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
    RowLayout { Layout.fillWidth:true
        SecondaryButton { text:"Remove Green"; compact:true; onClicked:VideoStudio.applyChromaPreset(layer.id,"green") }
        SecondaryButton { text:"Remove Blue"; compact:true; onClicked:VideoStudio.applyChromaPreset(layer.id,"blue") }
        SecondaryButton { text:"Off"; compact:true; onClicked:VideoStudio.setChroma(layer.id,false,"#00FF00",.18,.08) }
    }
    RowLayout { Layout.fillWidth:true
        SecondaryButton { text:"Layer Down"; compact:true; onClicked:VideoStudio.moveLayerZ(layer.id,-1) }
        SecondaryButton { text:"Layer Up"; compact:true; onClicked:VideoStudio.moveLayerZ(layer.id,1) }
        SecondaryButton { text:"Duplicate"; compact:true; onClicked:VideoStudio.duplicateLayer(layer.id) }
        SecondaryButton { text:"Remove"; compact:true; onClicked:VideoStudio.deleteLayer(layer.id) }
    }
}
