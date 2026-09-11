import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id:root
    property var controller
    property bool enabledDucking:true
    property real amountDb:-12
    implicitHeight:112
    ColumnLayout { anchors.fill:parent;anchors.margins:Theme.spacing.md;spacing:Theme.spacing.sm
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true;spacing:1
                Text { text:"Lower music while speaking";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall;font.weight:Theme.type.semibold }
                Text { text:"Timing-based ducking follows voice clips and returns smoothly between speech.";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;wrapMode:Text.WordWrap;Layout.fillWidth:true }
            }
            AppSwitch { checked:root.enabledDucking;onToggled:{root.enabledDucking=checked;if(root.controller)root.controller.setMusicDucking(checked,root.amountDb)} }
        }
        RowLayout { Layout.fillWidth:true;enabled:root.enabledDucking
            Text { text:"Duck";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
            Slider { Layout.fillWidth:true;from:-24;to:-3;value:root.amountDb;stepSize:1;onPressedChanged:{if(!pressed){root.amountDb=value;if(root.controller)root.controller.setMusicDucking(root.enabledDucking,value)}} }
            Text { text:root.amountDb.toFixed(0)+" dB";color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
        }
    }
}
