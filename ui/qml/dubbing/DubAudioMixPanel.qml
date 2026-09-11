import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    required property var controller
    implicitHeight:210
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.sm
        Text { text:"6 · Audio mix"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            Text { text:"Mode"; color:Theme.colors.textSecondary }
            ComboBox { id:mode; model:["replace","mix","duck","custom"]; currentIndex:Math.max(0,model.indexOf(controller.mixSettings.mode||"duck")) }
            Item { Layout.fillWidth:true }
            Text { visible:mode.currentText!=="replace"; text:"Original speech may remain audible."; color:Theme.colors.textMuted }
        }
        RowLayout { Layout.fillWidth:true
            Text { text:"Original"; color:Theme.colors.textSecondary }
            Slider { id:original; from:0; to:1.5; value:Number(controller.mixSettings.originalVolume||0.25); Layout.fillWidth:true }
            Text { text:Math.round(original.value*100)+"%"; color:Theme.colors.textMuted }
            Text { text:"Dub"; color:Theme.colors.textSecondary }
            Slider { id:dub; from:0; to:1.5; value:Number(controller.mixSettings.dubVolume||1); Layout.fillWidth:true }
            Text { text:Math.round(dub.value*100)+"%"; color:Theme.colors.textMuted }
        }
        RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }
            SecondaryButton { text:"Save Mix"; onClicked:controller.updateMix(mode.currentText,original.value,dub.value,original.value,Math.min(original.value,0.12),120) }
            AppButton { text:"Rebuild Audio Mix"; onClicked:controller.rebuildMix() }
        }
    }
}
