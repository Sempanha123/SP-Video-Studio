import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var master:({})
    property var controller
    implicitWidth:150;implicitHeight:274
    ColumnLayout { anchors.fill:parent;anchors.margins:Theme.spacing.sm;spacing:Theme.spacing.sm
        Text { text:"Master";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.heading;font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            StatusBadge { text:master.limiterEnabled?"Limiter On":"Limiter Off";status:master.limiterEnabled?"ready":"unknown" }
            Item { Layout.fillWidth:true }
            AppSwitch { checked:master.limiterEnabled!==false;onToggled:if(root.controller)root.controller.setMasterLimiter(checked) }
        }
        RowLayout { Layout.alignment:Qt.AlignHCenter;AudioMeter { peakDb:Number(master.peakDb||-60) };Slider { orientation:Qt.Vertical;from:-60;to:12;value:Number(master.masterGainDb||0);stepSize:.5;Layout.preferredHeight:128;onPressedChanged:if(!pressed&&controller)controller.setMasterGain(value) } }
        Text { Layout.alignment:Qt.AlignHCenter;text:Number(master.masterGainDb||0).toFixed(1)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        Text { Layout.fillWidth:true;text:master.normalizationEnabled?"Loudness normalization enabled":"Peak-safe final output";wrapMode:Text.WordWrap;color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
    }
}
